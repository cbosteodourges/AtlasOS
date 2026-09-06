package fr.atlasos.connect

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

class AtlasSyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        AtlasSyncCoordinator.run(applicationContext)
        Result.success()
    } catch (_: SecurityException) {
        Result.success()
    } catch (_: Exception) {
        Result.retry()
    }
}
