package fr.atlasos.connect

import android.os.Bundle
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.lifecycle.lifecycleScope
import androidx.work.WorkManager
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val dataPermissions = setOf(
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(RestingHeartRateRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(SpeedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class),
        HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(StepsCadenceRecord::class),
        HealthPermission.getReadPermission(PowerRecord::class),
        HealthPermission.getReadPermission(WeightRecord::class),
        HealthPermission.getReadPermission(BodyFatRecord::class),
        HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
        HealthPermission.getReadPermission(OxygenSaturationRecord::class),
        HealthPermission.getReadPermission(RespiratoryRateRecord::class),
        HealthPermission.getReadPermission(BodyTemperatureRecord::class),
        HealthPermission.getReadPermission(BloodPressureRecord::class),
        HealthPermission.getReadPermission(HydrationRecord::class),
        HealthPermission.getReadPermission(NutritionRecord::class),
    )
    private val permissions = dataPermissions + setOf(
        HealthPermission.PERMISSION_READ_HEALTH_DATA_HISTORY,
    )
    private val requestPermissions = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) {
        lifecycleScope.launch {
            val granted = HealthConnectClient.getOrCreate(this@MainActivity)
                .permissionController.getGrantedPermissions()
            val missingData = dataPermissions - granted
            val missingExtra = permissions - dataPermissions - granted
            status.text = when {
                missingData.isNotEmpty() -> "Autorisations de données manquantes : ${missingData.size}"
                missingExtra.isNotEmpty() -> "Données autorisées · historique à compléter"
                else -> "Autorisations accordées · synchronisation manuelle prête"
            }
        }
    }
    private lateinit var server: EditText
    private lateinit var code: EditText
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WorkManager.getInstance(this).cancelUniqueWork("atlas-health-sync")
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 64, 48, 48) }
        layout.addView(TextView(this).apply { text = "Atlas Connect"; textSize = 28f })
        server = EditText(this).apply { hint = "Adresse Atlas, ex. http://192.168.0.37:8011" }
        code = EditText(this).apply { hint = "Code à 6 chiffres"; inputType = 2 }
        status = TextView(this).apply { text = "Non associé"; setPadding(0, 24, 0, 24) }
        val permissionsButton = Button(this).apply { text = "Autoriser Santé Connect"; setOnClickListener { requestPermissions.launch(permissions) } }
        val pairButton = Button(this).apply { text = "Associer ce téléphone"; setOnClickListener { pair() } }
        val syncButton = Button(this).apply { text = "Synchroniser Atlas · santé et activités"; setOnClickListener { sync() } }
        listOf(server, code, permissionsButton, pairButton, syncButton, status).forEach(layout::addView)
        setContentView(layout)
        val prefs = getSharedPreferences("atlas", MODE_PRIVATE)
        server.setText(prefs.getString("server", ""))
        if (prefs.contains("token")) {
            status.text = "Téléphone associé · appuyez sur le bouton pour tout synchroniser"
        }
    }

    private fun pair() = lifecycleScope.launch {
        try {
            val token = AtlasTransport.pair(server.text.toString(), code.text.toString())
            getSharedPreferences("atlas", MODE_PRIVATE).edit().putString("server", server.text.toString().trimEnd('/')).putString("token", token).apply()
            status.text = "Association réussie · synchronisation manuelle prête"
        } catch (error: Exception) { status.text = error.message ?: "Échec de l’association" }
    }

    private fun sync() = lifecycleScope.launch {
        status.text = "Synchronisation de la santé et des activités…"
        status.text = try {
            val count = HealthSync(this@MainActivity).run()
            "Synchronisation terminée : $count éléments santé et activités"
        } catch (error: Exception) { error.message ?: "Échec" }
    }
}
