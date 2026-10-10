package dev.androidstack.verification

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.json.JSONObject

/**
 * Shared scaffolding for a project's journey tests: timing spans + terminal oracle hook.
 *
 * The project subclasses this, drives the UI inside [action] blocks and asserts inside
 * [observe] blocks, then calls [verify]. `verify` is the terminal ground-truth decision —
 * the layer only consumes the resulting `verify-part.json`.
 */
abstract class JourneyBase {

    protected val inst get() = InstrumentationRegistry.getInstrumentation()
    protected val device get() = UiDevice.getInstance(inst)
    protected val ctx get() = inst.targetContext

    /** The package under test, resolved from the target context (never hardcoded). */
    protected val appPackage: String get() = ctx.packageName

    /** A UI-driving span -> T7b. */
    protected fun action(name: String, block: () -> Unit) {
        TimingLogger.actionStart(name)
        try {
            block()
        } finally {
            TimingLogger.actionEnd(name)
        }
    }

    /** An observation/assertion span -> T7c. */
    protected fun observe(name: String, block: () -> Unit) {
        TimingLogger.evidenceStart(name)
        try {
            block()
        } finally {
            TimingLogger.evidenceEnd(name)
        }
    }

    /** Lets scoped autosave/commit work settle before navigating away. */
    protected fun settle(ms: Long = 600) {
        Thread.sleep(ms)
    }

    /**
     * Terminal oracle hook. A project overrides this to write its own `verify-part.json`
     * through a Verifier-like object.
     *
     * Fail-closed default (v1.0.1): an un-overridden `verify()` returns outcome FAIL, never
     * PASS. A journey that forgets its terminal oracle therefore cannot produce a passing
     * verdict, and — with the host evidence gate — cannot yield an overall PASS either.
     * Journeys that rely on a separate `oracle` class in the plan still override this to
     * write their part (or the separate oracle writes it); they must not rely on the default.
     */
    protected open fun verify(): JSONObject =
        JSONObject()
            .put("journey", VerificationEnv.journey())
            .put("outcome", "FAIL")
            .put("error", "verify() not implemented: a journey must supply a terminal oracle")
}
