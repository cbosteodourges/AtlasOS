package fr.atlasos.connect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ChangesTokenRequest
import androidx.health.connect.client.records.Record
import kotlin.reflect.KClass

/**
 * Lightweight differential gate in front of the proven HealthSync importer.
 *
 * First run performs the normal safe import and establishes a Health Connect
 * change token. Later background runs do no heavy read/upload when Health
 * Connect has not changed. If changes exist, HealthSync performs its existing
 * bounded/idempotent import, then the token is advanced only after success.
 * This is intentionally migration-safe: a failed upload never consumes data.
 */
class HealthChangeSync(private val context: Context) {
    companion object {
        private const val TOKEN_KEY = "health_changes_token_v1"
    }

    private val recordTypes: Set<KClass<out Record>> = setOf(
        ExerciseSessionRecord::class,
        SleepSessionRecord::class,
        HeartRateRecord::class,
        RestingHeartRateRecord::class,
        HeartRateVariabilityRmssdRecord::class,
        DistanceRecord::class,
        SpeedRecord::class,
        ElevationGainedRecord::class,
        TotalCaloriesBurnedRecord::class,
        ActiveCaloriesBurnedRecord::class,
        BasalMetabolicRateRecord::class,
        StepsRecord::class,
        FloorsClimbedRecord::class,
        StepsCadenceRecord::class,
        PowerRecord::class,
        WeightRecord::class,
        BodyFatRecord::class,
        HeightRecord::class,
        LeanBodyMassRecord::class,
        BodyWaterMassRecord::class,
        BoneMassRecord::class,
        Vo2MaxRecord::class,
        OxygenSaturationRecord::class,
        RespiratoryRateRecord::class,
        BodyTemperatureRecord::class,
        BloodPressureRecord::class,
        HydrationRecord::class,
        NutritionRecord::class,
    )

    suspend fun run(onProgress: (Int, String) -> Unit = { _, _ -> }): Int {
        val client = HealthConnectClient.getOrCreate(context)
        val prefs = context.getSharedPreferences("atlas", Context.MODE_PRIVATE)
        val oldToken = prefs.getString(TOKEN_KEY, null)

        if (oldToken == null) {
            onProgress(2, "Initialisation de la synchronisation différentielle")
            val count = HealthSync(context).run(onProgress)
            val token = client.getChangesToken(ChangesTokenRequest(recordTypes = recordTypes))
            prefs.edit().putString(TOKEN_KEY, token).apply()
            return count
        }

        var cursor = oldToken
        var changed = false
        while (true) {
            val response = client.getChanges(cursor)
            if (response.changesTokenExpired) {
                // Safe fallback: do not risk a gap after >30 days or a platform
                // reset. Re-import the bounded window and establish a new base.
                onProgress(2, "Jeton expiré · rattrapage Santé Connect")
                val count = HealthSync(context).run(onProgress)
                val token = client.getChangesToken(ChangesTokenRequest(recordTypes = recordTypes))
                prefs.edit().putString(TOKEN_KEY, token).apply()
                return count
            }
            if (response.changes.isNotEmpty()) changed = true
            cursor = response.nextChangesToken
            if (!response.hasMore) break
        }

        if (!changed) {
            // Advancing an empty token keeps it alive and avoids expiry while
            // ensuring the next run starts from the newest HC checkpoint.
            prefs.edit().putString(TOKEN_KEY, cursor).apply()
            onProgress(100, "Santé Connect déjà à jour")
            return 0
        }

        onProgress(10, "Nouvelles données Santé Connect détectées")
        val count = HealthSync(context).run(onProgress)
        // Critical ordering: advance only after Atlas acknowledged the upload.
        prefs.edit().putString(TOKEN_KEY, cursor).apply()
        return count
    }
}
