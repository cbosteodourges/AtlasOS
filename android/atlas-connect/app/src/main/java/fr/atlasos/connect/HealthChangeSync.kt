package fr.atlasos.connect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.changes.DeletionChange
import androidx.health.connect.client.changes.UpsertionChange
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ChangesTokenRequest
import kotlin.reflect.KClass

class HealthChangeSync(private val context: Context) {
    companion object { private const val TOKEN_KEY="health_changes_token_v2" }
    private val candidateTypes:Set<KClass<out Record>> = setOf(ExerciseSessionRecord::class,SleepSessionRecord::class,HeartRateRecord::class,RestingHeartRateRecord::class,HeartRateVariabilityRmssdRecord::class,DistanceRecord::class,SpeedRecord::class,ElevationGainedRecord::class,TotalCaloriesBurnedRecord::class,ActiveCaloriesBurnedRecord::class,BasalMetabolicRateRecord::class,StepsRecord::class,FloorsClimbedRecord::class,StepsCadenceRecord::class,CyclingPedalingCadenceRecord::class,PowerRecord::class,WeightRecord::class,BodyFatRecord::class,HeightRecord::class,LeanBodyMassRecord::class,BodyWaterMassRecord::class,BoneMassRecord::class,Vo2MaxRecord::class,OxygenSaturationRecord::class,RespiratoryRateRecord::class,BodyTemperatureRecord::class,BloodPressureRecord::class,HydrationRecord::class,NutritionRecord::class)
    private suspend fun grantedTypes(client:HealthConnectClient):Set<KClass<out Record>>{val granted=client.permissionController.getGrantedPermissions();return candidateTypes.filterTo(linkedSetOf()){HealthPermission.getReadPermission(it) in granted}}
    suspend fun run(onProgress:(Int,String)->Unit={_,_->}):Int{
        val client=HealthConnectClient.getOrCreate(context);val prefs=context.getSharedPreferences("atlas",Context.MODE_PRIVATE);val recordTypes=grantedTypes(client);require(recordTypes.isNotEmpty()){"Aucun type Santé Connect autorisé"}
        val signature=recordTypes.map{it.qualifiedName?:it.simpleName?:"?"}.sorted().joinToString("|").hashCode();val signatureKey="health_changes_permissions_v2";var oldToken=prefs.getString(TOKEN_KEY,null)
        if(prefs.getInt(signatureKey,Int.MIN_VALUE)!=signature){oldToken=null;prefs.edit().remove(TOKEN_KEY).putInt(signatureKey,signature).apply()}
        if(oldToken==null){onProgress(2,"Initialisation différentielle · ${recordTypes.size} types autorisés");val count=HealthSync(context).run(onProgress);val token=client.getChangesToken(ChangesTokenRequest(recordTypes=recordTypes));prefs.edit().putString(TOKEN_KEY,token).putInt(signatureKey,signature).apply();return count}
        var cursor:String=oldToken;val upserts=mutableListOf<Record>();val deletions=linkedSetOf<String>()
        while(true){val response=client.getChanges(cursor);if(response.changesTokenExpired){onProgress(2,"Jeton expiré · rattrapage Santé Connect");val count=HealthSync(context).run(onProgress);val token=client.getChangesToken(ChangesTokenRequest(recordTypes=recordTypes));prefs.edit().putString(TOKEN_KEY,token).apply();return count}
            response.changes.forEach{change->when(change){is UpsertionChange->if(change.record.metadata.dataOrigin.packageName!=context.packageName)upserts.add(change.record);is DeletionChange->deletions.add(change.recordId)}};response.nextChangesToken?.let{cursor=it};if(!response.hasMore)break}
        if(upserts.isEmpty()&&deletions.isEmpty()){prefs.edit().putString(TOKEN_KEY,cursor).apply();onProgress(100,"Santé Connect déjà à jour");return 0}
        onProgress(10,"${upserts.size+deletions.size} changement(s) Santé Connect détecté(s)")
        val delta=HealthDeltaSync(context)
        val count=if(delta.requiresActivityRebuild(upserts)){
            onProgress(20,"Activité modifiée · enrichissement complet de la séance")
            HealthSync(context).run(onProgress)
        }else{
            delta.send(upserts,deletions,onProgress)
        }
        // Consume changes only after Atlas acknowledged the upload.
        prefs.edit().putString(TOKEN_KEY,cursor).apply();onProgress(100,"Atlas à jour · delta confirmé");return count
    }
}
