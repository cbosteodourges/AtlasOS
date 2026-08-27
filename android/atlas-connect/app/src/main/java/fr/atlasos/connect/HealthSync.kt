package fr.atlasos.connect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.temporal.ChronoUnit

class HealthSync(private val context: Context) {
    suspend fun run(): Int {
        require(HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) { "Santé Connect indisponible" }
        val client = HealthConnectClient.getOrCreate(context)
        val prefs = context.getSharedPreferences("atlas", Context.MODE_PRIVATE)
        val last = prefs.getLong("last_sync", 0L)
        val start = if (last > 0) Instant.ofEpochMilli(last).minus(1, ChronoUnit.DAYS) else Instant.now().minus(10, ChronoUnit.YEARS)
        val range = TimeRangeFilter.between(start, Instant.now())
        val activities = JSONArray()
        client.readRecords(ReadRecordsRequest(ExerciseSessionRecord::class, range)).records.forEach { record ->
            activities.put(JSONObject().put("source_id", record.metadata.id).put("type", "exercise")
                .put("start_time", record.startTime.toString()).put("duration_seconds", record.endTime.epochSecond - record.startTime.epochSecond)
                .put("source_device", record.metadata.dataOrigin.packageName))
        }
        val wellness = JSONArray()
        client.readRecords(ReadRecordsRequest(SleepSessionRecord::class, range)).records.forEach { record ->
            wellness.put(JSONObject().put("source_id", record.metadata.id).put("type", "sleep")
                .put("start_time", record.startTime.toString()).put("end_time", record.endTime.toString())
                .put("duration_seconds", record.endTime.epochSecond - record.startTime.epochSecond))
        }
        AtlasTransport.ingest(prefs.getString("server", "")!!, prefs.getString("token", "")!!,
            JSONObject().put("activities", activities).put("wellness", wellness))
        prefs.edit().putLong("last_sync", System.currentTimeMillis()).apply()
        return activities.length() + wellness.length()
    }
}
