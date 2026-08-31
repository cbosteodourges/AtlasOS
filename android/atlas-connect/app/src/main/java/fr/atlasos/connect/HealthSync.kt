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
import java.time.ZoneId
import java.time.temporal.ChronoUnit

class HealthSync(private val context: Context) {
    companion object {
        private const val SYNC_SCHEMA_VERSION = 4
    }
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

    suspend fun run(onProgress: (Int, String) -> Unit = { _, _ -> }): Int {
        require(HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) { "Santé Connect indisponible" }
        val client = HealthConnectClient.getOrCreate(context)
        onProgress(5, "Lecture des données Health Connect")
        val granted = client.permissionController.getGrantedPermissions()
        val skipped = JSONArray()
        val prefs = context.getSharedPreferences("atlas", Context.MODE_PRIVATE)
        val last = prefs.getLong("last_sync", 0L)
        val previousSchema = prefs.getInt("sync_schema_version", 0)
        val backfillPerformed = previousSchema < SYNC_SCHEMA_VERSION
        // Chaque nouvelle version du schéma relit dix ans d'historique afin que
        // les types ajoutés ne restent pas vides derrière l'ancien filigrane.
        val start = if (last > 0 && !backfillPerformed) {
            Instant.ofEpochMilli(last).minus(1, ChronoUnit.DAYS)
        } else {
            Instant.now().minus(30, ChronoUnit.DAYS)
        }
        val end = Instant.now()
        val range = TimeRangeFilter.between(start, end)
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
        val vo2MaxRecords = client.availableRecords<Vo2MaxRecord>(range, granted, skipped)
        val heightRecords = client.availableRecords<HeightRecord>(range, granted, skipped)
        val leanBodyMassRecords = client.availableRecords<LeanBodyMassRecord>(range, granted, skipped)
        val bodyWaterMassRecords = client.availableRecords<BodyWaterMassRecord>(range, granted, skipped)
        val boneMassRecords = client.availableRecords<BoneMassRecord>(range, granted, skipped)
        val sleepRecords = client.availableRecords<SleepSessionRecord>(range, granted, skipped)
        val restingHeartRates = client.availableRecords<RestingHeartRateRecord>(range, granted, skipped)
        val hrvRecords = client.availableRecords<HeartRateVariabilityRmssdRecord>(range, granted, skipped)
        val weightRecords = client.availableRecords<WeightRecord>(range, granted, skipped)
        val bodyFatRecords = client.availableRecords<BodyFatRecord>(range, granted, skipped)
        val oxygenRecords = client.availableRecords<OxygenSaturationRecord>(range, granted, skipped)
        val respiratoryRecords = client.availableRecords<RespiratoryRateRecord>(range, granted, skipped)
        val temperatureRecords = client.availableRecords<BodyTemperatureRecord>(range, granted, skipped)
        val pressureRecords = client.availableRecords<BloodPressureRecord>(range, granted, skipped)
        val hydrationRecords = client.availableRecords<HydrationRecord>(range, granted, skipped)
        val nutritionRecords = client.availableRecords<NutritionRecord>(range, granted, skipped)
        val stepRecords = client.availableRecords<StepsRecord>(range, granted, skipped)
        val floorRecords = client.availableRecords<FloorsClimbedRecord>(range, granted, skipped)

        val heartRateSamples = heartRates.asSequence()
            .flatMap { it.samples.asSequence() }
            .filter { !it.time.isBefore(start) && it.time.isBefore(end) }
            .toList()
        val speedSamples = speeds.asSequence()
            .flatMap { it.samples.asSequence() }
            .filter { !it.time.isBefore(start) && it.time.isBefore(end) }
            .toList()
        val cadenceSamples = cadences.asSequence()
            .flatMap { it.samples.asSequence() }
            .filter { !it.time.isBefore(start) && it.time.isBefore(end) }
            .toList()
        val powerSamples = powers.asSequence()
            .flatMap { it.samples.asSequence() }
            .filter { !it.time.isBefore(start) && it.time.isBefore(end) }
            .toList()

        onProgress(35, "Préparation des activités")
        val activities = JSONArray()
        exercises.forEach { exercise ->
            val hr = heartRateSamples.filter { it.time in exercise.startTime..exercise.endTime }
            val speed = speedSamples.filter { it.time in exercise.startTime..exercise.endTime }
            val cadence = cadenceSamples.filter { it.time in exercise.startTime..exercise.endTime }
            val power = powerSamples.filter { it.time in exercise.startTime..exercise.endTime }
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
                .put("start_time", exercise.startTime).put("local_day", localDay(exercise.startTime))
                .put("duration_seconds", exercise.endTime.epochSecond - exercise.startTime.epochSecond)
                .put("lap_count", exercise.laps.size).put("segment_count", exercise.segments.size)
                .put("distance_meters", distance).put("calories_kcal", kcal).put("elevation_gain_m", ascent)
                .putNullable("average_heart_rate_bpm", hr.map { it.beatsPerMinute.toDouble() }.averageOrNull())
                .putNullable("maximum_heart_rate_bpm", hr.maxOfOrNull { it.beatsPerMinute })
                .putNullable("average_speed_mps", speed.map { it.speed.inMetersPerSecond }.averageOrNull())
                .put("samples", samples).put("source_device", exercise.metadata.dataOrigin.packageName))
        }
        val wellness = JSONArray()
        calories.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "total_calories_burned").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("local_day", localDay(it.startTime))
            .put("energy_kcal", it.energy.inKilocalories).put("source_device", it.metadata.dataOrigin.packageName)) }
        activeCalories.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "active_calories_burned").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("local_day", localDay(it.startTime))
            .put("energy_kcal", it.energy.inKilocalories).put("source_device", it.metadata.dataOrigin.packageName)) }
        basalRates.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "basal_metabolic_rate").put("start_time", it.time).put("local_day", localDay(it.time))
            .put("basal_kcal_per_day", it.basalMetabolicRate.inWatts * 86400.0 / 4184.0)
            .put("source_device", it.metadata.dataOrigin.packageName)) }
        sleepRecords.forEach { sleep ->
            val stages = JSONArray()
            sleep.stages.forEach {
                stages.put(JSONObject()
                    .put("stage", it.stage)
                    .put("start_time", it.startTime)
                    .put("end_time", it.endTime))
            }

            val sessionSeconds =
                sleep.endTime.epochSecond - sleep.startTime.epochSecond
            val awakeSeconds = sleep.stages
                .filter { it.stage in setOf(1, 3, 7) }
                .sumOf { it.endTime.epochSecond - it.startTime.epochSecond }
            val explicitSleepSeconds = sleep.stages
                .filter { it.stage in setOf(2, 4, 5, 6) }
                .sumOf { it.endTime.epochSecond - it.startTime.epochSecond }
            val actualSleepSeconds = if (explicitSleepSeconds > 0) {
                explicitSleepSeconds
            } else {
                maxOf(0L, sessionSeconds - awakeSeconds)
            }

            wellness.put(JSONObject()
                .put("source_id", sleep.metadata.id)
                .put("type", "sleep")
                .put("start_time", sleep.startTime)
                .put("end_time", sleep.endTime)
                .put("local_day", localDay(sleep.endTime.minus(1, ChronoUnit.SECONDS)))
                .put("source_device", sleep.metadata.dataOrigin.packageName)
                .put("session_duration_seconds", sessionSeconds)
                .put("awake_duration_seconds", awakeSeconds)
                .put("duration_seconds", actualSleepSeconds)
                .put("stages", stages))
        }
        restingHeartRates.forEach { wellness.put(instant(it.metadata.id, "resting_heart_rate", it.time, it.beatsPerMinute)) }
        hrvRecords.forEach { wellness.put(instant(it.metadata.id, "hrv_rmssd", it.time, it.heartRateVariabilityMillis)) }
        weightRecords.forEach { wellness.put(instant(it.metadata.id, "weight", it.time, it.weight.inKilograms)) }
        bodyFatRecords.forEach { wellness.put(instant(it.metadata.id, "body_fat", it.time, it.percentage.value, it.metadata.dataOrigin.packageName)) }
        heightRecords.forEach { wellness.put(instant(it.metadata.id, "height", it.time, it.height.inMeters, it.metadata.dataOrigin.packageName)) }
        leanBodyMassRecords.forEach { wellness.put(instant(it.metadata.id, "lean_body_mass", it.time, it.mass.inKilograms, it.metadata.dataOrigin.packageName)) }
        bodyWaterMassRecords.forEach { wellness.put(instant(it.metadata.id, "body_water_mass", it.time, it.mass.inKilograms, it.metadata.dataOrigin.packageName)) }
        boneMassRecords.forEach { wellness.put(instant(it.metadata.id, "bone_mass", it.time, it.mass.inKilograms, it.metadata.dataOrigin.packageName)) }
        vo2MaxRecords.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "vo2_max").put("start_time", it.time).put("local_day", localDay(it.time))
            .put("value", it.vo2MillilitersPerMinuteKilogram).put("measurement_method", it.measurementMethod)
            .put("source_device", it.metadata.dataOrigin.packageName)) }
        oxygenRecords.forEach { wellness.put(instant(it.metadata.id, "oxygen_saturation", it.time, it.percentage.value)) }
        respiratoryRecords.forEach { wellness.put(instant(it.metadata.id, "respiratory_rate", it.time, it.rate)) }
        temperatureRecords.forEach { wellness.put(instant(it.metadata.id, "body_temperature", it.time, it.temperature.inCelsius)) }
        pressureRecords.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "blood_pressure").put("start_time", it.time).put("local_day", localDay(it.time))
            .put("source_device", it.metadata.dataOrigin.packageName)
            .put("systolic_mmhg", it.systolic.inMillimetersOfMercury)
            .put("diastolic_mmhg", it.diastolic.inMillimetersOfMercury)) }
        hydrationRecords.forEach { wellness.put(JSONObject().put("source_id", it.metadata.id)
            .put("type", "hydration").put("start_time", it.startTime).put("end_time", it.endTime)
            .put("local_day", localDay(it.startTime)).put("volume_ml", it.volume.inLiters * 1000).put("source_device", it.metadata.dataOrigin.packageName)) }
        nutritionRecords.forEach { nutrition -> wellness.put(JSONObject()
            .put("source_id", nutrition.metadata.id).put("type", "nutrition")
            .put("start_time", nutrition.startTime).put("end_time", nutrition.endTime)
            .putNullable("energy_kcal", nutrition.energy?.inKilocalories)
            .putNullable("protein_g", nutrition.protein?.inGrams)
            .putNullable("carbohydrate_g", nutrition.totalCarbohydrate?.inGrams)
            .putNullable("fat_g", nutrition.totalFat?.inGrams)
            .putNullable("fiber_g", nutrition.dietaryFiber?.inGrams)
            .putNullable("sodium_mg", nutrition.sodium?.inGrams?.times(1000))
            .putNullable("sugar_g", nutrition.sugar?.inGrams)
            .putNullable("calcium_mg", nutrition.calcium?.inGrams?.times(1000))
            .putNullable("iron_mg", nutrition.iron?.inGrams?.times(1000))
            .putNullable("magnesium_mg", nutrition.magnesium?.inGrams?.times(1000))
            .putNullable("potassium_mg", nutrition.potassium?.inGrams?.times(1000))
            .putNullable("zinc_mg", nutrition.zinc?.inGrams?.times(1000))
            .putNullable("vitamin_c_mg", nutrition.vitaminC?.inGrams?.times(1000))
            .putNullable("vitamin_d_mcg", nutrition.vitaminD?.inGrams?.times(1000000))
            .putNullable("vitamin_b12_mcg", nutrition.vitaminB12?.inGrams?.times(1000000))
            .putNullable("caffeine_mg", nutrition.caffeine?.inGrams?.times(1000))
            .put("local_day", localDay(nutrition.startTime))
            .put("meal_type", nutrition.mealType).put("name", nutrition.name)
            .put("source_device", nutrition.metadata.dataOrigin.packageName)) }
        stepRecords.forEach { wellness.put(interval(it.metadata.id, "steps", it.startTime, it.endTime, it.count)) }
        floorRecords.forEach { wellness.put(interval(it.metadata.id, "floors", it.startTime, it.endTime, it.floors)) }
        heartRates.groupBy { it.metadata.dataOrigin.packageName }
            .forEach { (source, records) ->
                val samples = records.asSequence()
                    .flatMap { it.samples.asSequence() }
                    .filter { !it.time.isBefore(start) && it.time.isBefore(end) }
                    .distinctBy { it.time to it.beatsPerMinute }
                    .sortedBy { it.time }
                    .toList()

                samples.chunked(5000).forEachIndexed { index, chunk ->
                    if (chunk.isNotEmpty()) {
                        wellness.put(JSONObject()
                            .put("source_id", "heart-rate:${source.hashCode()}:${start.epochSecond}:$index")
                            .put("type", "heart_rate_series")
                            .put("start_time", chunk.first().time)
                            .put("end_time", chunk.last().time)
                            .put("local_day", localDay(chunk.first().time))
                            .put("source_device", source)
                            .put("samples", JSONArray(chunk.map {
                                JSONObject()
                                    .put("timestamp", it.time)
                                    .put("value", it.beatsPerMinute)
                            })))
                    }
                }
            }

        val inventory = JSONArray(listOf(
            inventoryEntry("ExerciseSessionRecord", exercises),
            inventoryEntry("SleepSessionRecord", sleepRecords),
            inventoryEntry("HeartRateRecord", heartRates),
            inventoryEntry("RestingHeartRateRecord", restingHeartRates),
            inventoryEntry("HeartRateVariabilityRmssdRecord", hrvRecords),
            inventoryEntry("Vo2MaxRecord", vo2MaxRecords),
            inventoryEntry("WeightRecord", weightRecords),
            inventoryEntry("BodyFatRecord", bodyFatRecords),
            inventoryEntry("HeightRecord", heightRecords),
            inventoryEntry("LeanBodyMassRecord", leanBodyMassRecords),
            inventoryEntry("BodyWaterMassRecord", bodyWaterMassRecords),
            inventoryEntry("BoneMassRecord", boneMassRecords),
            inventoryEntry("TotalCaloriesBurnedRecord", calories),
            inventoryEntry("ActiveCaloriesBurnedRecord", activeCalories),
            inventoryEntry("BasalMetabolicRateRecord", basalRates),
            inventoryEntry("HydrationRecord", hydrationRecords),
            inventoryEntry("NutritionRecord", nutritionRecords),
            inventoryEntry("StepsRecord", stepRecords),
            inventoryEntry("FloorsClimbedRecord", floorRecords)
        ))
        val server = prefs.getString("server", "")!!
        val token = prefs.getString("token", "")!!
        onProgress(55, "Préparation des lots")
        val maximumBatchCharacters = 1_500_000
        val batches = mutableListOf<Pair<JSONArray, JSONArray>>()
        var activityOffset = 0
        var wellnessOffset = 0

        while (activityOffset < activities.length() || wellnessOffset < wellness.length()) {
            val activityBatch = JSONArray()
            val wellnessBatch = JSONArray()
            var estimatedCharacters = 0

            while (activityOffset < activities.length()) {
                val item = activities.getJSONObject(activityOffset)
                val itemCharacters = item.toString().length
                if (estimatedCharacters > 0 &&
                    estimatedCharacters + itemCharacters > maximumBatchCharacters
                ) break
                activityBatch.put(item)
                activityOffset += 1
                estimatedCharacters += itemCharacters
            }

            while (wellnessOffset < wellness.length()) {
                val item = wellness.getJSONObject(wellnessOffset)
                val itemCharacters = item.toString().length
                if (estimatedCharacters > 0 &&
                    estimatedCharacters + itemCharacters > maximumBatchCharacters
                ) break
                wellnessBatch.put(item)
                wellnessOffset += 1
                estimatedCharacters += itemCharacters
            }

            batches.add(activityBatch to wellnessBatch)
        }

        onProgress(55, "Transmission de ${batches.size} lots vers Atlas OS")
        batches.forEachIndexed { index, (activityBatch, wellnessBatch) ->
            AtlasTransport.ingest(
                server,
                token,
                JSONObject()
                    .put("activities", activityBatch)
                    .put("wellness", wellnessBatch)
                    .put("record_inventory", inventory)
                    .put("skipped_record_types", skipped)
                    .put("sync_schema_version", SYNC_SCHEMA_VERSION)
                    .put("backfill_performed", backfillPerformed)
                    .put("sync_complete", index == batches.lastIndex)
            )
            val completed = index + 1
            val percent = 55 + (completed * 40 / batches.size)
            onProgress(
                percent.coerceAtMost(95),
                "Envoi du lot $completed sur ${batches.size}"
            )
        }
        prefs.edit().putLong("last_sync", System.currentTimeMillis())
            .putInt("sync_schema_version", SYNC_SCHEMA_VERSION).apply()
        onProgress(100, "Synchronisation terminée")
        return activities.length() + wellness.length()
    }

    private fun overlaps(start: Instant, end: Instant, exercise: ExerciseSessionRecord) = start < exercise.endTime && end > exercise.startTime
    private fun List<Double>.averageOrNull(): Double? = if (isEmpty()) null else average()
    private fun JSONObject.putNullable(key: String, value: Number?): JSONObject = if (value == null) this else put(key, value)
    private fun localDay(time: Instant): String = time.atZone(ZoneId.systemDefault()).toLocalDate().toString()
    private fun inventoryEntry(type: String, records: List<out Record>): JSONObject {
        val sources = records.map { it.metadata.dataOrigin.packageName }.filter { it.isNotBlank() }.distinct().sorted()
        return JSONObject().put("record_type", type).put("count", records.size).put("sources", JSONArray(sources))
    }
    private fun instant(id: String, type: String, time: Instant, value: Number, source: String? = null) =
        JSONObject().put("source_id", id).put("type", type).put("start_time", time)
            .put("local_day", localDay(time)).put("value", value).apply { if (!source.isNullOrBlank()) put("source_device", source) }
    private fun interval(id: String, type: String, start: Instant, end: Instant, value: Number) =
        JSONObject().put("source_id", id).put("type", type).put("start_time", start).put("end_time", end)
            .put("local_day", localDay(start)).put("value", value)
}
