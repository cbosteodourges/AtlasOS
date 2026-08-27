package fr.atlasos.connect

import android.os.Bundle
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.lifecycle.lifecycleScope
import androidx.work.*
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    private val permissions = setOf(
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.PERMISSION_READ_HEALTH_DATA_HISTORY,
        HealthPermission.PERMISSION_READ_HEALTH_DATA_IN_BACKGROUND,
    )
    private val requestPermissions = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted -> status.text = if (granted.containsAll(permissions)) "Autorisations accordées" else "Autorisations incomplètes" }
    private lateinit var server: EditText
    private lateinit var code: EditText
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 64, 48, 48) }
        layout.addView(TextView(this).apply { text = "Atlas Connect"; textSize = 28f })
        server = EditText(this).apply { hint = "Adresse Atlas, ex. http://192.168.0.37:8010" }
        code = EditText(this).apply { hint = "Code à 6 chiffres"; inputType = 2 }
        status = TextView(this).apply { text = "Non associé"; setPadding(0, 24, 0, 24) }
        val permissionsButton = Button(this).apply { text = "Autoriser Santé Connect"; setOnClickListener { requestPermissions.launch(permissions) } }
        val pairButton = Button(this).apply { text = "Associer ce téléphone"; setOnClickListener { pair() } }
        val syncButton = Button(this).apply { text = "Synchroniser maintenant"; setOnClickListener { sync() } }
        listOf(server, code, permissionsButton, pairButton, syncButton, status).forEach(layout::addView)
        setContentView(layout)
        val prefs = getSharedPreferences("atlas", MODE_PRIVATE)
        server.setText(prefs.getString("server", ""))
        if (prefs.contains("token")) status.text = "Téléphone associé"
    }

    private fun pair() = lifecycleScope.launch {
        try {
            val token = AtlasTransport.pair(server.text.toString(), code.text.toString())
            getSharedPreferences("atlas", MODE_PRIVATE).edit().putString("server", server.text.toString().trimEnd('/')).putString("token", token).apply()
            scheduleBackgroundSync(); status.text = "Association réussie"
        } catch (error: Exception) { status.text = error.message ?: "Échec de l’association" }
    }

    private fun sync() = lifecycleScope.launch {
        status.text = "Synchronisation…"
        status.text = try { HealthSync(this@MainActivity).run(); "Synchronisation terminée" } catch (error: Exception) { error.message ?: "Échec" }
    }

    private fun scheduleBackgroundSync() {
        val request = PeriodicWorkRequestBuilder<AtlasSyncWorker>(6, TimeUnit.HOURS).setConstraints(
            Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork("atlas-health-sync", ExistingPeriodicWorkPolicy.UPDATE, request)
    }
}
