package dev.androidstack.verification

import android.content.Context
import android.content.Intent
import androidx.test.uiautomator.By
import androidx.test.uiautomator.BySelector
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until

/**
 * Small UiAutomator helpers shared by journey tests.
 *
 * The app package is injected, never hardcoded: construct with the package under test
 * (`UiDriver(appPackage)` or `UiDriver.fromLaunchIntent(ctx)`).
 */
class UiDriver(private val appPackage: String) {

    companion object {
        /** Resolve the launcher package from a context (returns null if none). */
        fun fromLaunchIntent(ctx: Context): UiDriver? {
            val pkg = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)?.`package`
                ?: ctx.packageName
            return UiDriver(pkg)
        }
    }

    fun launchApp(device: UiDevice, ctx: Context, readySelector: BySelector? = null) {
        val intent = ctx.packageManager.getLaunchIntentForPackage(appPackage)
            ?: error("no launch intent for $appPackage")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ctx.startActivity(intent)
        if (readySelector != null) device.wait(Until.hasObject(readySelector), 10_000)
        else device.waitForIdle()
    }

    fun waitFor(device: UiDevice, selector: BySelector, timeout: Long = 5_000): Boolean =
        device.wait(Until.hasObject(selector), timeout)

    fun obj(device: UiDevice, selector: BySelector, timeout: Long = 5_000): UiObject2 =
        device.wait(Until.findObject(selector), timeout)
            ?: error("no node found for $selector")

    fun clickDesc(device: UiDevice, desc: String) {
        obj(device, By.desc(desc)).click()
        device.waitForIdle()
    }

    fun clickText(device: UiDevice, text: String) {
        obj(device, By.text(text)).click()
        device.waitForIdle()
    }

    /** All editable fields currently on screen, in tree order. */
    fun fields(device: UiDevice): List<UiObject2> {
        device.wait(Until.hasObject(By.clazz("android.widget.EditText")), 5_000)
        return device.findObjects(By.clazz("android.widget.EditText"))
    }

    fun type(device: UiDevice, index: Int, text: String) {
        val f = fields(device)
        require(index < f.size) { "edit field $index missing (found ${f.size})" }
        f[index].click()
        f[index].setText(text)
        device.waitForIdle()
    }
}
