package fr.atlasos.connect

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object AtlasTransport {
    suspend fun pair(server: String, code: String): String = withContext(Dispatchers.IO) {
        val result = post("${server.trimEnd('/')}/api/atlas/health-connect/pair",
            JSONObject().put("code", code).put("device", JSONObject().put("model", android.os.Build.MODEL)), null)
        result.getString("token")
    }
    suspend fun ingest(server: String, token: String, payload: JSONObject) = withContext(Dispatchers.IO) {
        post("${server.trimEnd('/')}/api/atlas/health-connect/ingest", payload, token)
    }
    private fun post(url: String, payload: JSONObject, token: String?): JSONObject {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"; connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json")
        if (token != null) connection.setRequestProperty("Authorization", "Bearer $token")
        connection.outputStream.use { it.write(payload.toString().toByteArray()) }
        val text = (if (connection.responseCode < 400) connection.inputStream else connection.errorStream).bufferedReader().readText()
        val result = JSONObject(text)
        if (connection.responseCode >= 400) error(result.optString("error", "Erreur Atlas"))
        return result
    }
}
