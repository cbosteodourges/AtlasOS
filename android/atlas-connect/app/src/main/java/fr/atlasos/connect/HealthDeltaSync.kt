package fr.atlasos.connect

import android.content.Context
import androidx.health.connect.client.records.*
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.ZoneId
import java.time.temporal.ChronoUnit

/** Sends Health Connect upserts directly when they are self-contained wellness
 * records. Exercise sessions and their component streams still use the proven
 * bounded importer until the rich activity delta path is migrated separately. */
class HealthDeltaSync(private val context: Context) {
    fun requiresActivityRebuild(records: List<Record>): Boolean = records.any {
        it is ExerciseSessionRecord || it is DistanceRecord || it is SpeedRecord ||
            it is ElevationGainedRecord || it is StepsCadenceRecord || it is PowerRecord
    }

    suspend fun send(records: List<Record>, deletedIds: Set<String>, onProgress: (Int, String) -> Unit): Int {
        val prefs = context.getSharedPreferences("atlas", Context.MODE_PRIVATE)
        val server = prefs.getString("server", "").orEmpty()
        val token = prefs.getString("token", "").orEmpty()
        require(server.isNotBlank() && token.isNotBlank()) { "Téléphone Atlas non associé" }
        val wellness = JSONArray()
        records.forEach { record -> serialize(record)?.let(wellness::put) }
        if (wellness.length() == 0 && deletedIds.isEmpty()) return 0
        onProgress(45, "Préparation du delta Santé Connect")
        AtlasTransport.ingest(server, token, JSONObject()
            .put("activities", JSONArray())
            .put("wellness", wellness)
            .put("deleted_source_ids", JSONArray(deletedIds.toList()))
            .put("record_inventory", JSONArray())
            .put("skipped_record_types", JSONArray())
            .put("sync_schema_version", 8)
            .put("delta_sync", true)
            .put("sync_complete", true))
        onProgress(95, "Delta transmis à Atlas")
        return wellness.length() + deletedIds.size
    }

    private fun serialize(record: Record): JSONObject? = when (record) {
        is TotalCaloriesBurnedRecord -> interval(record.metadata.id,"total_calories_burned",record.startTime,record.endTime,record.energy.inKilocalories, "energy_kcal", source(record))
        is ActiveCaloriesBurnedRecord -> interval(record.metadata.id,"active_calories_burned",record.startTime,record.endTime,record.energy.inKilocalories,"energy_kcal",source(record))
        is BasalMetabolicRateRecord -> instant(record.metadata.id,"basal_metabolic_rate",record.time,record.basalMetabolicRate.inWatts*86400.0/4184.0,"basal_kcal_per_day",source(record))
        is SleepSessionRecord -> sleep(record)
        is RestingHeartRateRecord -> instant(record.metadata.id,"resting_heart_rate",record.time,record.beatsPerMinute,"value",source(record))
        is HeartRateVariabilityRmssdRecord -> instant(record.metadata.id,"hrv_rmssd",record.time,record.heartRateVariabilityMillis,"value",source(record))
        is WeightRecord -> instant(record.metadata.id,"weight",record.time,record.weight.inKilograms,"value",source(record))
        is BodyFatRecord -> instant(record.metadata.id,"body_fat",record.time,record.percentage.value,"value",source(record))
        is HeightRecord -> instant(record.metadata.id,"height",record.time,record.height.inMeters,"value",source(record))
        is LeanBodyMassRecord -> instant(record.metadata.id,"lean_body_mass",record.time,record.mass.inKilograms,"value",source(record))
        is BodyWaterMassRecord -> instant(record.metadata.id,"body_water_mass",record.time,record.mass.inKilograms,"value",source(record))
        is BoneMassRecord -> instant(record.metadata.id,"bone_mass",record.time,record.mass.inKilograms,"value",source(record))
        is Vo2MaxRecord -> instant(record.metadata.id,"vo2_max",record.time,record.vo2MillilitersPerMinuteKilogram,"value",source(record)).put("measurement_method",record.measurementMethod)
        is OxygenSaturationRecord -> instant(record.metadata.id,"oxygen_saturation",record.time,record.percentage.value,"value",source(record))
        is RespiratoryRateRecord -> instant(record.metadata.id,"respiratory_rate",record.time,record.rate,"value",source(record))
        is BodyTemperatureRecord -> instant(record.metadata.id,"body_temperature",record.time,record.temperature.inCelsius,"value",source(record))
        is BloodPressureRecord -> instant(record.metadata.id,"blood_pressure",record.time,record.systolic.inMillimetersOfMercury,"systolic_mmhg",source(record)).put("diastolic_mmhg",record.diastolic.inMillimetersOfMercury)
        is HydrationRecord -> interval(record.metadata.id,"hydration",record.startTime,record.endTime,record.volume.inLiters*1000,"volume_ml",source(record))
        is NutritionRecord -> nutrition(record)
        is StepsRecord -> interval(record.metadata.id,"steps",record.startTime,record.endTime,record.count,"value",source(record))
        is FloorsClimbedRecord -> interval(record.metadata.id,"floors",record.startTime,record.endTime,record.floors,"value",source(record))
        is HeartRateRecord -> JSONObject().put("source_id",record.metadata.id).put("type","heart_rate_series")
            .put("start_time",record.startTime).put("end_time",record.endTime).put("local_day",localDay(record.startTime)).put("source_device",source(record))
            .put("samples",JSONArray(record.samples.map{JSONObject().put("timestamp",it.time).put("value",it.beatsPerMinute)}))
        else -> null
    }

    private fun sleep(r: SleepSessionRecord): JSONObject {
        val session=r.endTime.epochSecond-r.startTime.epochSecond
        val awake=r.stages.filter{it.stage in setOf(1,3,7)}.sumOf{it.endTime.epochSecond-it.startTime.epochSecond}
        val explicit=r.stages.filter{it.stage in setOf(2,4,5,6)}.sumOf{it.endTime.epochSecond-it.startTime.epochSecond}
        return JSONObject().put("source_id",r.metadata.id).put("type","sleep").put("start_time",r.startTime).put("end_time",r.endTime)
            .put("local_day",localDay(r.endTime.minus(1,ChronoUnit.SECONDS))).put("source_device",source(r)).put("session_duration_seconds",session)
            .put("awake_duration_seconds",awake).put("duration_seconds",if(explicit>0)explicit else maxOf(0,session-awake))
            .put("stages",JSONArray(r.stages.map{JSONObject().put("stage",it.stage).put("start_time",it.startTime).put("end_time",it.endTime)}))
    }
    private fun nutrition(r:NutritionRecord)=JSONObject().put("source_id",r.metadata.id).put("type","nutrition").put("start_time",r.startTime).put("end_time",r.endTime)
        .putNullable("energy_kcal",r.energy?.inKilocalories).putNullable("protein_g",r.protein?.inGrams).putNullable("carbohydrate_g",r.totalCarbohydrate?.inGrams)
        .putNullable("fat_g",r.totalFat?.inGrams).putNullable("fiber_g",r.dietaryFiber?.inGrams).putNullable("sugar_g",r.sugar?.inGrams)
        .put("local_day",localDay(r.startTime)).put("meal_type",r.mealType).put("name",r.name).put("source_device",source(r))
    private fun instant(id:String,type:String,time:Instant,value:Number,key:String,source:String)=JSONObject().put("source_id",id).put("type",type).put("start_time",time).put("local_day",localDay(time)).put(key,value).put("source_device",source)
    private fun interval(id:String,type:String,start:Instant,end:Instant,value:Number,key:String,source:String)=JSONObject().put("source_id",id).put("type",type).put("start_time",start).put("end_time",end).put("local_day",localDay(start)).put(key,value).put("source_device",source)
    private fun source(r:Record)=r.metadata.dataOrigin.packageName
    private fun localDay(t:Instant)=t.atZone(ZoneId.systemDefault()).toLocalDate().toString()
    private fun JSONObject.putNullable(key:String,value:Number?)=if(value==null)this else put(key,value)
}
