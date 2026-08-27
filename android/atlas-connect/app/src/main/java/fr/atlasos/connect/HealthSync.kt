package fr.atlasos.connect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
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

    suspend fun run(): Int {
        require(HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) { "Santé Connect indisponible" }
        val client = HealthConnectClient.getOrCreate(context)
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
        val exercises = client.records<ExerciseSessionRecord>(range)
        val heartRates = client.records<HeartRateRecord>(range)
        val distances = client.records<DistanceRecord>(range)
        val speeds = client.records<SpeedRecord>(range)
        val elevations = client.records<ElevationGainedRecord>(range)
        val calories = client.records<TotalCaloriesBurnedRecord>(range)
        val cadences = client.records<StepsCadenceRecord>(range)
        val powers = client.records<PowerRecord>(range)
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
            val kcal = calories.filter { overlaps(it.startTime, it.endTime, exercise) }.sumOf { it.energy.inKilocalories }
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
        client.records<SleepSessionRecord>(range).forEach { sleep ->
            val stages = JSONArray()
            sleep.stages.forEach { stages.put(JSONObject().put("stage", it.stage).put("start_time", it.startTime).put("end_time", it.endTime)) }
            wellness.put(JSONObject().put("source_id", sleep.metadata.id).put("type", "sleep")
                .put("start_time", sleep.startTime).put("end_time", sleep.endTime)
                .put("duration_seconds", sleep.endTime.epochSecond - sleep.startTime.epochSecond).put("stages", stages))
        }
        client.records<RestingHeartRateRecord>(range).forEach { wellness.put(instant(it.metadata.id, "resting_heart_rate", it.time, it.beatsPerMinute)) }
        client.records<HeartRateVariabilityRmssdRecord>(range).forEach { wellness.put(instant(it.metadata.id, "hrv_rmssd", it.time, it.heartRateVariabilityMillis)) }
        client.records<WeightRecord>(range).forEach { wellness.put(instant(it.metadata.id, "weight", it.time, it.weight.inKilograms)) }
        client.records<BodyFatRecord>(range).forEach { wellness.put(instant(it.metadata.id, "body_fat", it.time, it.percentage.value)) }
        client.records<OxygenSaturationRecord>(range).forEach { wellness.put(instant(it.metadata.id, "oxygen_saturation", it.time, it.percentage.value)) }
        client.records<RespiratoryRateRecord>(range).forEach { wellness.put(instant(it.metadata.id, "respiratory_rate", it.time, it.rate)) }
        client.records<BodyTemperatureRecord>(range).forEach { wellness.put(instant(it.metadata.id, "body_temperature", it.time, it.temperature.inCelsius)) }
        client.records<BloodPressureRecord>(range).forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "blood_pressure").put("start_time", it.time)
            .put("systolic_mmhg", it.systolic.inMillimetersOfMercury)
            .put("diastolic_mmhg", it.diastolic.inMillimetersOfMercury)) }
        client.records<HydrationRecord>(range).forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "hydration").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("volume_ml", it.volume.inLiters * 1000).put("source_device", it.metadata.dataOrigin.packageName)) }
        client.records<NutritionRecord>(range).forEach { nutrition -> wellness.put(JSONObject()
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
        client.records<StepsRecord>(range).forEach { wellness.put(interval(it.metadata.id, "steps", it.startTime, it.endTime, it.count)) }
        client.records<FloorsClimbedRecord>(range).forEach { wellness.put(interval(it.metadata.id, "floors", it.startTime, it.endTime, it.floors)) }
        heartRates.forEach { record -> wellness.put(JSONObject().put("source_id", record.metadata.id).put("type", "heart_rate_series")
            .put("start_time", record.startTime).put("end_time", record.endTime)
            .put("samples", JSONArray(record.samples.map { JSONObject().put("timestamp", it.time).put("value", it.beatsPerMinute) }))) }
        AtlasTransport.ingest(prefs.getString("server", "")!!, prefs.getString("token", "")!!,
            JSONObject().put("activities", activities).put("wellness", wellness))
        prefs.edit().putLong("last_sync", System.currentTimeMillis()).apply()
        return activities.length() + wellness.length()
    }

    private fun overlaps(start: Instant, end: Instant, exercise: ExerciseSessionRecord) = start < exercise.endTime && end > exercise.startTime
    private fun List<Double>.averageOrNull(): Double? = if (isEmpty()) null else average()
    private fun JSONObject.putNullable(key: String, value: Number?): JSONObject = if (value == null) this else put(key, value)
    private fun instant(id: String, type: String, time: Instant, value: Number) = JSONObject().put("source_id", id).put("type", type).put("start_time", time).put("value", value)
    private fun interval(id: String, type: String, start: Instant, end: Instant, value: Number) = JSONObject().put("source_id", id).put("type", type).put("start_time", start).put("end_time", end).put("value", value)
}
