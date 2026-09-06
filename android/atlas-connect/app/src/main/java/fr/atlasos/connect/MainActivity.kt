package fr.atlasos.connect

import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private val navy = Color.rgb(2, 13, 24)
    private val card = Color.rgb(7, 29, 45)
    private val cyan = Color.rgb(49, 214, 255)
    private val atlasTextColor = Color.rgb(235, 246, 255)
    private val muted = Color.rgb(143, 168, 187)
    private var autoSyncStarted = false

    private val dataPermissions = setOf(
        HealthPermission.getReadPermission(ExerciseSessionRecord::class), HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class), HealthPermission.getReadPermission(RestingHeartRateRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class), HealthPermission.getReadPermission(SpeedRecord::class),
        HealthPermission.getReadPermission(ElevationGainedRecord::class), HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class), HealthPermission.getReadPermission(BasalMetabolicRateRecord::class),
        HealthPermission.getReadPermission(StepsRecord::class), HealthPermission.getReadPermission(FloorsClimbedRecord::class),
        HealthPermission.getReadPermission(StepsCadenceRecord::class), HealthPermission.getReadPermission(PowerRecord::class),
        HealthPermission.getReadPermission(WeightRecord::class), HealthPermission.getReadPermission(BodyFatRecord::class),
        HealthPermission.getReadPermission(HeightRecord::class), HealthPermission.getReadPermission(LeanBodyMassRecord::class),
        HealthPermission.getReadPermission(BodyWaterMassRecord::class), HealthPermission.getReadPermission(BoneMassRecord::class),
        HealthPermission.getReadPermission(Vo2MaxRecord::class), HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
        HealthPermission.getReadPermission(OxygenSaturationRecord::class), HealthPermission.getReadPermission(RespiratoryRateRecord::class),
        HealthPermission.getReadPermission(BodyTemperatureRecord::class), HealthPermission.getReadPermission(BloodPressureRecord::class),
        HealthPermission.getReadPermission(HydrationRecord::class), HealthPermission.getReadPermission(NutritionRecord::class),
    )
    private val permissions = dataPermissions + HealthPermission.PERMISSION_READ_HEALTH_DATA_HISTORY
    private lateinit var server: EditText
    private lateinit var code: EditText
    private lateinit var status: TextView
    private lateinit var syncButton: Button

    private val requestPermissions = registerForActivityResult(PermissionController.createRequestPermissionResultContract()) {
        lifecycleScope.launch {
            val granted = HealthConnectClient.getOrCreate(this@MainActivity).permissionController.getGrantedPermissions()
            val missingData = dataPermissions - granted
            val missingExtra = permissions - dataPermissions - granted
            showStatus(when {
                missingData.isNotEmpty() -> "Autorisations manquantes : ${missingData.size}"
                missingExtra.isNotEmpty() -> "Données autorisées · historique à compléter"
                else -> "Autorisations accordées · synchronisation prête"
            }, missingData.isEmpty())
            if (missingData.isEmpty()) autoSyncOnOpen()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = navy
        window.navigationBarColor = navy
        val page = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL; setPadding(dp(24), dp(30), dp(24), dp(32)); setBackgroundColor(navy) }
        page.addView(ImageView(this).apply { setImageResource(R.drawable.atlas_logo); scaleType = ImageView.ScaleType.CENTER_CROP }, LinearLayout.LayoutParams(dp(82), dp(82)).apply { bottomMargin = dp(16) })
        page.addView(TextView(this).apply { text = "ATLAS CONNECT"; textSize = 26f; setTextColor(atlasTextColor); gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD); letterSpacing = 0.08f })
        page.addView(TextView(this).apply { text = "Votre passerelle personnelle vers Atlas OS"; textSize = 14f; setTextColor(muted); gravity = Gravity.CENTER }, match().apply { topMargin = dp(5); bottomMargin = dp(24) })

        val connectionCard = verticalCard(); connectionCard.addView(sectionTitle("CONNEXION ATLAS"))
        server = field("Adresse du serveur Atlas"); code = field("Code d’association à 6 chiffres").apply { inputType = InputType.TYPE_CLASS_NUMBER }
        connectionCard.addView(server, match().apply { topMargin = dp(12) }); connectionCard.addView(code, match().apply { topMargin = dp(10) })
        connectionCard.addView(actionButton("Associer ce téléphone", false) { pair() }, match(dp(48)).apply { topMargin = dp(12) }); page.addView(connectionCard, match())

        val syncCard = verticalCard(); syncCard.addView(sectionTitle("SANTÉ ET ACTIVITÉS"))
        syncCard.addView(TextView(this).apply { text = "À l’ouverture, Atlas vérifie automatiquement Santé Connect. Le bouton ci-dessous permet de forcer une synchronisation."; textSize = 14f; setTextColor(muted); setLineSpacing(0f, 1.15f) }, match().apply { topMargin = dp(8) })
        syncCard.addView(actionButton("Autoriser Santé Connect", false) { requestPermissions.launch(permissions) }, match(dp(48)).apply { topMargin = dp(16) })
        syncButton = actionButton("Synchroniser Atlas", true) { sync(force = true) }; syncCard.addView(syncButton, match(dp(56)).apply { topMargin = dp(10) }); page.addView(syncCard, match().apply { topMargin = dp(16) })

        status = TextView(this).apply { text = "Non associé"; textSize = 14f; setTextColor(muted); gravity = Gravity.CENTER; setPadding(dp(12), dp(15), dp(12), dp(15)); background = rounded(Color.rgb(5, 24, 38), Color.rgb(17, 61, 84), 14f) }
        page.addView(status, match().apply { topMargin = dp(16) })
        setContentView(ScrollView(this).apply { isFillViewport = true; setBackgroundColor(navy); addView(page) })

        val prefs = getSharedPreferences("atlas", MODE_PRIVATE); server.setText(prefs.getString("server", ""))
        if (prefs.contains("token")) { showStatus("Téléphone associé · vérification automatique…", true); AtlasAutoSync.schedule(this); autoSyncOnOpen() }
    }

    private fun autoSyncOnOpen() {
        if (autoSyncStarted) return
        val prefs = getSharedPreferences("atlas", MODE_PRIVATE)
        if (!prefs.contains("token") || prefs.getString("server", "").isNullOrBlank()) return
        autoSyncStarted = true
        lifecycleScope.launch {
            try {
                val granted = HealthConnectClient.getOrCreate(this@MainActivity).permissionController.getGrantedPermissions()
                if ((dataPermissions - granted).isNotEmpty()) { showStatus("Santé Connect doit être autorisé"); return@launch }
                showStatus("Vérification Santé Connect…")
                val count = withContext(Dispatchers.Default) {
                    HealthChangeSync(this@MainActivity).run { percent, message -> runOnUiThread { showStatus("$message · $percent %") } }
                }
                showStatus(if (count == 0) "Atlas à jour · aucune nouvelle donnée" else "Atlas à jour · $count éléments transmis", true)
            } catch (error: Exception) { showStatus("Synchronisation automatique : ${error.message ?: "échec"}") }
        }
    }

    private fun pair() = lifecycleScope.launch {
        showStatus("Association en cours…")
        try {
            val token = AtlasTransport.pair(server.text.toString(), code.text.toString())
            getSharedPreferences("atlas", MODE_PRIVATE).edit().putString("server", server.text.toString().trimEnd('/')).putString("token", token).apply()
            AtlasAutoSync.schedule(this@MainActivity); showStatus("Association réussie · synchronisation automatique activée", true); autoSyncOnOpen()
        } catch (error: Exception) { showStatus(error.message ?: "Échec de l’association") }
    }

    private fun sync(force: Boolean = false) = lifecycleScope.launch {
        syncButton.isEnabled = false; showStatus(if (force) "Synchronisation forcée · 0 %" else "Préparation · 0 %")
        try {
            val visibleServer = server.text.toString().trim().trimEnd('/'); require(visibleServer.isNotEmpty()) { "Adresse du serveur Atlas manquante." }
            getSharedPreferences("atlas", MODE_PRIVATE).edit().putString("server", visibleServer).apply()
            val count = withContext(Dispatchers.Default) { HealthSync(this@MainActivity).run { percent, message -> runOnUiThread { showStatus("$message · $percent %") } } }
            showStatus("Transmission terminée · $count éléments transmis", true)
        } catch (error: Exception) { showStatus(error.message ?: "Échec de la synchronisation") } finally { syncButton.isEnabled = true }
    }

    private fun showStatus(message: String, success: Boolean = false) { if (!::status.isInitialized) return; status.text = message; status.setTextColor(if (success) Color.rgb(89, 234, 181) else muted) }
    private fun verticalCard() = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(18), dp(18), dp(18), dp(18)); background = rounded(card, Color.rgb(16, 65, 88), 20f) }
    private fun sectionTitle(value: String) = TextView(this).apply { text = value; textSize = 12f; setTextColor(cyan); setTypeface(typeface, Typeface.BOLD); letterSpacing = 0.12f }
    private fun field(placeholder: String) = EditText(this).apply { hint = placeholder; setHintTextColor(Color.rgb(100, 128, 148)); setTextColor(atlasTextColor); textSize = 14f; setSingleLine(true); setPadding(dp(14), 0, dp(14), 0); background = rounded(Color.rgb(3, 20, 32), Color.rgb(20, 75, 100), 12f) }
    private fun actionButton(label: String, primary: Boolean, action: () -> Unit) = Button(this).apply { text = label; textSize = if (primary) 16f else 14f; setTextColor(if (primary) navy else atlasTextColor); setTypeface(typeface, Typeface.BOLD); isAllCaps = false; background = rounded(if (primary) cyan else Color.rgb(10, 42, 61), if (primary) cyan else Color.rgb(23, 91, 120), 14f); setOnClickListener { action() } }
    private fun rounded(fill: Int, stroke: Int, radius: Float) = GradientDrawable().apply { shape = GradientDrawable.RECTANGLE; setColor(fill); setStroke(dp(1), stroke); cornerRadius = dp(radius.toInt()).toFloat() }
    private fun match(height: Int = ViewGroup.LayoutParams.WRAP_CONTENT) = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, height)
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}
