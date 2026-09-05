package fr.atlasos.connect

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.NoRouteToHostException
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException

object AtlasTransport {
    private const val CONNECT_TIMEOUT_MS = 8_000
    // Le calcul physiologique est lancé en arrière-plan par le PC : la réponse
    // ne dépend plus de la durée de l'analyse complète.
    private const val READ_TIMEOUT_MS = 45_000

    internal fun normalizeServer(server: String): String {
        val trimmed = server.trim().trimEnd('/')
        require(trimmed.isNotEmpty()) {
            "Adresse du serveur Atlas manquante."
        }
        return if (
            trimmed.startsWith("http://") ||
            trimmed.startsWith("https://")
        ) {
            trimmed
        } else {
            "http://$trimmed"
        }
    }

    suspend fun pair(server: String, code: String): String =
        withContext(Dispatchers.IO) {
            val base = normalizeServer(server)
            val result = post(
                "$base/api/atlas/health-connect/pair",
                JSONObject()
                    .put("code", code)
                    .put(
                        "device",
                        JSONObject().put(
                            "model",
                            android.os.Build.MODEL
                        )
                    ),
                null
            )
            result.getString("token")
        }

    suspend fun ingest(
        server: String,
        token: String,
        payload: JSONObject
    ) = withContext(Dispatchers.IO) {
        val base = normalizeServer(server)
        post(
            "$base/api/atlas/health-connect/ingest",
            payload,
            token
        )
    }

    private fun post(
        url: String,
        payload: JSONObject,
        token: String?
    ): JSONObject {
        val destination = URL(url)
        try {
            val connection =
                destination.openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.setRequestProperty(
                "Content-Type",
                "application/json; charset=utf-8"
            )
            if (token != null) {
                connection.setRequestProperty(
                    "Authorization",
                    "Bearer $token"
                )
            }
            connection.outputStream.use {
                it.write(
                    payload.toString()
                        .toByteArray(Charsets.UTF_8)
                )
            }
            val responseCode = connection.responseCode
            val stream = if (responseCode < 400) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            val text = stream
                ?.bufferedReader(Charsets.UTF_8)
                ?.use { it.readText() }
                .orEmpty()
            val result = if (text.isBlank()) {
                JSONObject().put(
                    "error",
                    "Réponse vide de la passerelle Atlas."
                )
            } else {
                JSONObject(text)
            }
            if (responseCode >= 400) {
                error(
                    result.optString(
                        "error",
                        "Erreur Atlas HTTP $responseCode"
                    )
                )
            }
            return result
        } catch (error: UnknownHostException) {
            throw IllegalStateException(
                "Adresse Atlas introuvable : " +
                    "${destination.host}. Vérifiez l’adresse du PC.",
                error
            )
        } catch (error: NoRouteToHostException) {
            throw IllegalStateException(
                "Passerelle Atlas inaccessible à " +
                    "${destination.host}:${destination.portOrDefault()}. " +
                    "Vérifiez le Wi-Fi et le pare-feu Windows.",
                error
            )
        } catch (error: ConnectException) {
            throw IllegalStateException(
                "Connexion refusée par " +
                    "${destination.host}:${destination.portOrDefault()}. " +
                    "Redémarrez la passerelle Atlas et vérifiez le pare-feu.",
                error
            )
        } catch (error: SocketTimeoutException) {
            throw IllegalStateException(
                "Délai dépassé vers " +
                    "${destination.host}:${destination.portOrDefault()}. " +
                    "La transmission n'a pas été confirmée. Vérifiez que le PC " +
                    "reste allumé et connecté au même Wi-Fi.",
                error
            )
        }
    }

    private fun URL.portOrDefault(): Int =
        if (port >= 0) port else defaultPort
}
