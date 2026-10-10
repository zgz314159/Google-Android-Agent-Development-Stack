package dev.androidstack.verification

import android.content.Context
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import java.io.File

/**
 * Run identity + artifact locations, taken from instrumentation arguments.
 *
 * Contract (see ../../docs/FAILURE-EVIDENCE-CONTRACT.md):
 *   -e runId <id>     the Verification Layer run identity
 *   -e journey <id>   the journey identity from the verification plan
 */
object VerificationEnv {
    private val args get() = InstrumentationRegistry.getArguments()

    fun runId(): String = args.getString("runId") ?: "adhoc"
    fun journey(): String = args.getString("journey") ?: "unknown"

    fun outDir(context: Context): File {
        val d = File(context.getExternalFilesDir(null) ?: context.filesDir, "bench")
        if (!d.exists()) d.mkdirs()
        return d
    }
}

/**
 * Machine-readable event log for one verification run. Spans are paired START/END by name
 * and the host derives wall time from the monotonic `elapsed_realtime_ns` stamps — never
 * from log text or estimates. Writes `events-<runId>.jsonl` into the bench dir, exactly the
 * file the host pulls and parses.
 */
object TimingLogger {
    private var file: File? = null
    private var runId: String = "adhoc"
    private var journey: String = "unknown"

    fun begin(context: Context, runId: String, journey: String) {
        this.runId = runId
        this.journey = journey
        val f = File(VerificationEnv.outDir(context), "events-$runId.jsonl")
        f.writeText("")
        file = f
        event("RUN_START", "run")
    }

    fun actionStart(name: String) = event("ACTION_START", name)
    fun actionEnd(name: String) = event("ACTION_END", name)
    fun assertStart(name: String) = event("ASSERT_START", name)
    fun assertEnd(name: String) = event("ASSERT_END", name)
    fun evidenceStart(name: String) = event("EVIDENCE_START", name)
    fun evidenceEnd(name: String) = event("EVIDENCE_END", name)
    fun runEnd() = event("RUN_END", "run")

    private fun event(kind: String, name: String) {
        val f = file ?: return
        f.appendText(
            JSONObject()
                .put("kind", kind)
                .put("name", name)
                .put("run_id", runId)
                .put("journey", journey)
                .put("elapsed_realtime_ns", SystemClock.elapsedRealtimeNanos())
                .put("epoch_ms", System.currentTimeMillis())
                .toString() + "\n",
        )
    }
}
