package fr.atlasos.connect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.health.connect.client.permission.HealthPermission
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.temporal.ChronoUnit

class HealthSync(private val context: Context) {
    private suspend inline fun <reified T : Record> HealthConnectClient.records(range: TimeRangeFilter): List<T> {
        val result = mutableListOf<T>()
        var token: String? = null
        do {
            val page = readRecords(ReadRecordsRequest(T::class, range, pageSize = 1000, pageToken = token))
            result.addAll(page.records)
            token = page.pageToken
        } while (token != null)
        return result
    }

    private suspend inline fun <reified T : Record> HealthConnectClient.availableRecords(
        range: TimeRangeFilter,
        granted: Set<String>,
        skipped: JSONArray,
    ): List<T> {
        val permission = HealthPermission.getReadPermission(T::class)
        if (permission !in granted) {
            skipped.put(JSONObject().put("record_type", T::class.simpleName).put("reason", "permission_absent"))
            return emptyList()
        }
        return try {
            records<T>(range)
        } catch (error: Exception) {
            skipped.put(JSONObject().put("record_type", T::class.simpleName)
                .put("reason", error.message ?: error.javaClass.simpleName))
            emptyList()
        }
    }

    suspend fun run(): Int {
        require(HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) { "Santé Connect indisponible" }
        val client = HealthConnectClient.getOrCreate(context)
        val granted = client.permissionController.getGrantedPermissions()
        val skipped = JSONArray()
        val prefs = context.getSharedPreferences("atlas", Context.MODE_PRIVATE)
        val last = prefs.getLong("last_sync", 0L)
        // Instant supports fixed-duration units only. YEARS is calendar based and
        // throws UnsupportedTemporalTypeException on the first historical sync.
        val start = if (last > 0) {
            Instant.ofEpochMilli(last).minus(1, ChronoUnit.DAYS)
        } else {
            Instant.now().minus(3652, ChronoUnit.DAYS)
        }
        val range = TimeRangeFilter.between(start, Instant.now())
        val exercises = client.availableRecords<ExerciseSessionRecord>(range, granted, skipped)
        val heartRates = client.availableRecords<HeartRateRecord>(range, granted, skipped)
        val distances = client.availableRecords<DistanceRecord>(range, granted, skipped)
        val speeds = client.availableRecords<SpeedRecord>(range, granted, skipped)
        val elevations = client.availableRecords<ElevationGainedRecord>(range, granted, skipped)
        val calories = client.availableRecords<TotalCaloriesBurnedRecord>(range, granted, skipped)
        val activeCalories = client.availableRecords<ActiveCaloriesBurnedRecord>(range, granted, skipped)
        val basalRates = client.availableRecords<BasalMetabolicRateRecord>(range, granted, skipped)
        val cadences = client.availableRecords<StepsCadenceRecord>(range, granted, skipped)
        val powers = client.availableRecords<PowerRecord>(range, granted, skipped)
        val activities = JSONArray()
        exercises.forEach { exercise ->
            val hr = heartRates.flatMap { it.samples }.filter { it.time in exercise.startTime..exercise.endTime }
            val speed = speeds.flatMap { it.samples }.filter { it.time in exercise.startTime..exercise.endTime }
            val cadence = cadences.flatMap { it.samples }.filter { it.time in exercise.startTime..exercise.endTime }
            val power = powers.flatMap { it.samples }.filter { it.time in exercise.startTime..exercise.endTime }
            val samples = JSONArray()
            hr.forEach { samples.put(JSONObject().put("timestamp", it.time).put("heart_rate_bpm", it.beatsPerMinute)) }
            speed.forEach { samples.put(JSONObject().put("timestamp", it.time).put("speed_mps", it.speed.inMetersPerSecond)) }
            cadence.forEach { samples.put(JSONObject().put("timestamp", it.time).put("cadence_spm", it.rate)) }
            power.forEach { samples.put(JSONObject().put("timestamp", it.time).put("power_watts", it.power.inWatts)) }
            val distance = distances.filter { overlaps(it.startTime, it.endTime, exercise) }.sumOf { it.distance.inMeters }
            val activeKcal = activeCalories.filter { overlaps(it.startTime, it.endTime, exercise) }
                .sumOf { it.energy.inKilocalories }
            val kcal = if (activeKcal > 0) activeKcal else calories
                .filter { overlaps(it.startTime, it.endTime, exercise) }
                .sumOf { it.energy.inKilocalories }
            val ascent = elevations.filter { overlaps(it.startTime, it.endTime, exercise) }.sumOf { it.elevation.inMeters }
            activities.put(JSONObject().put("source_id", exercise.metadata.id).put("type", exercise.exerciseType)
                .put("start_time", exercise.startTime).put("duration_seconds", exercise.endTime.epochSecond - exercise.startTime.epochSecond)
                .put("distance_meters", distance).put("calories_kcal", kcal).put("elevation_gain_m", ascent)
                .putNullable("average_heart_rate_bpm", hr.map { it.beatsPerMinute.toDouble() }.averageOrNull())
                .putNullable("maximum_heart_rate_bpm", hr.maxOfOrNull { it.beatsPerMinute })
                .putNullable("average_speed_mps", speed.map { it.speed.inMetersPerSecond }.averageOrNull())
                .put("samples", samples).put("source_device", exercise.metadata.dataOrigin.packageName))
        }
        val wellness = JSONArray()
        calories.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "total_calories_burned").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("energy_kcal", it.energy.inKilocalories).put("source_device", it.metadata.dataOrigin.packageName)) }
        activeCalories.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "active_calories_burned").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("energy_kcal", it.energy.inKilocalories).put("source_device", it.metadata.dataOrigin.packageName)) }
        basalRates.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "basal_metabolic_rate").put("start_time", it.time)
            .put("basal_kcal_per_day", it.basalMetabolicRate.inWatts * 86400.0 / 4184.0)
            .put("source_device", it.metadata.dataOrigin.packageName)) }
        client.availableRecords<SleepSessionRecord>(range, granted, skipped).forEach { sleep ->
            val stages = JSONArray()
            sleep.stages.forEach { stages.put(JSONObject().put("stage", it.stage).put("start_time", it.startTime).put("end_time", it.endTime)) }
            wellness.put(JSONObject().put("source_id", sleep.metadata.id).put("type", "sleep")
                .put("start_time", sleep.startTime).put("end_time", sleep.endTime)
                .put("duration_seconds", sleep.endTime.epochSecond - sleep.startTime.epochSecond).put("stages", stages))
        }
        client.availableRecords<RestingHeartRateRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "resting_heart_rate", it.time, it.beatsPerMinute)) }
        client.availableRecords<HeartRateVariabilityRmssdRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "hrv_rmssd", it.time, it.heartRateVariabilityMillis)) }
        client.availableRecords<WeightRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "weight", it.time, it.weight.inKilograms)) }
        client.availableRecords<BodyFatRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "body_fat", it.time, it.percentage.value)) }
        client.availableRecords<OxygenSaturationRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "oxygen_saturation", it.time, it.percentage.value)) }
        client.availableRecords<RespiratoryRateRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "respiratory_rate", it.time, it.rate)) }
        client.availableRecords<BodyTemperatureRecord>(range, granted, skipped).forEach { wellness.put(instant(it.metadata.id, "body_temperature", it.time, it.temperature.inCelsius)) }
        client.availableRecords<BloodPressureRecord>(range, granted, skipped).forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "blood_pressure").put("start_time", it.time)
            .put("systolic_mmhg", it.systolic.inMillimetersOfMercury)
            .put("diastolic_mmhg", it.diastolic.inMillimetersOfMercury)) }
        client.availableRecords<HydrationRecord>(range, granted, skipped).forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "hydration").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("volume_ml", it.volume.inLiters * 1000).put("source_device", it.metadata.dataOrigin.packageName)) }
        client.availableRecords<NutritionRecord>(range, granted, skipped).forEach { nutrition -> wellness.put(JSONObject()
            .put("source_id", nutrition.metadata.id).put("type", "nutrition")
            .put("start_time", nutrition.startTime).put("end_time", nutrition.endTime)
            .putNullable("energy_kcal", nutrition.energy?.inKilocalories)
            .putNullable("protein_g", nutrition.protein?.inGrams)
            .putNullable("carbohydrate_g", nutrition.totalCarbohydrate?.inGrams)
            .putNullable("fat_g", nutrition.totalFat?.inGrams)
            .putNullable("fiber_g", nutrition.dietaryFiber?.inGrams)
            .putNullable("sodium_mg", nutrition.sodium?.inGrams?.times(1000))
            .put("meal_type", nutrition.mealType).put("name", nutrition.name)
            .put("source_device", nutrition.metadata.dataOrigin.packageName)) }
        client.availableRecords<StepsRecord>(range, granted, skipped).forEach { wellness.put(interval(it.metadata.id, "steps", it.startTime, it.endTime, it.count)) }
        client.availableRecords<FloorsClimbedRecord>(range, granted, skipped).forEach { wellness.put(interval(it.metadata.id, "floors", it.startTime, it.endTime, it.floors)) }
        heartRates.forEach { record -> wellness.put(JSONObject().put("source_id", record.metadata.id).put("type", "heart_rate_series")
            .put("start_time", record.startTime).put("end_time", record.endTime)
            .put("samples", JSONArray(record.samples.map { JSONObject().put("timestamp", it.time).put("value", it.beatsPerMinute) }))) }
        AtlasTransport.ingest(prefs.getString("server", "")!!, prefs.getString("token", "")!!,
            JSONObject().put("activities", activities).put("wellness", wellness).put("skipped_record_types", skipped))
        prefs.edit().putLong("last_sync", System.currentTimeMillis()).apply()
        return activities.length() + wellness.length()
    }

    private fun overlaps(start: Instant, end: Instant, exercise: ExerciseSessionRecord) = start < exercise.endTime && end > exercise.startTime
    private fun List<Double>.averageOrNull(): Double? = if (isEmpty()) null else average()
    private fun JSONObject.putNullable(key: String, value: Number?): JSONObject = if (value == null) this else put(key, value)
    private fun instant(id: String, type: String, time: Instant, value: Number) = JSONObject().put("source_id", id).put("type", type).put("start_time", time).put("value", value)
    private fun interval(id: String, type: String, start: Instant, end: Instant, value: Number) = JSONObject().put("source_id", id).put("type", type).put("start_time", start).put("end_time", end).put("value", value)
}
