package dev.androidstack.verification

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.json.JSONObject
import org.junit.rules.TestWatcher
import org.junit.runner.Description
import java.io.File

/**
 * On any assertion failure, automatically emits the failure bundle from inside the test
 * process (no human in the loop). The host harness adds layout.json, logcat.txt and
 * executor-output.txt on top of this.
 *
 * A project supplies the DB/domain state snapshot through [dbStateProvider] (defaults to a
 * minimal placeholder) so the bundle carries `db-state.json`.
 */
class FailureBundleRule(
    private val dbStateProvider: () -> JSONObject = { JSONObject() },
) : TestWatcher() {

    override fun failed(e: Throwable, description: Description) {
        runCatching {
            val inst = InstrumentationRegistry.getInstrumentation()
            val ctx = inst.targetContext
            val dir = File(VerificationEnv.outDir(ctx), "failure")
            if (!dir.exists()) dir.mkdirs()

            File(dir, "failed-assertion.json").writeText(
                JSONObject()
                    .put("test", description.toString())
                    .put("run_id", VerificationEnv.runId())
                    .put("journey", VerificationEnv.journey())
                    .put("exception", e.javaClass.name)
                    .put("message", e.message ?: "")
                    .toString(2),
            )

            val device = UiDevice.getInstance(inst)
            runCatching { device.takeScreenshot(File(dir, "screenshot.png")) }
            runCatching { File(dir, "db-state.json").writeText(dbStateProvider().toString(2)) }

            File(dir, "metadata.json").writeText(
                JSONObject()
                    .put("run_id", VerificationEnv.runId())
                    .put("journey", VerificationEnv.journey())
                    .put("timestamp_ms", System.currentTimeMillis())
                    .toString(2),
            )
        }
    }
}
