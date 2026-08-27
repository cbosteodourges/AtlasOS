package fr.atlasos.connect

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

class AtlasSyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try { HealthSync(applicationContext).run(); Result.success() } catch (_: Exception) { Result.retry() }
}
