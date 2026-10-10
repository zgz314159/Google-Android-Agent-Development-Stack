pluginManagement {
    repositories {
        // China-mainland mirrors first; official sources remain as fallback.
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        maven { url = uri("https://maven.aliyun.com/repository/central") }
        google {
            content {
                includeGroupByRegex("androidx.*")
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/central") }
        google {
            content {
                includeGroupByRegex("androidx.*")
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
            }
        }
        mavenCentral()
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

// Keep ALL build output OUTSIDE the project so a clean tree stays clean. The runner sets
// STACK_CACHE_ROOT; without it, builds fall back to the build/ dirs (gitignored).
val stackCache = System.getenv("STACK_CACHE_ROOT")
if (!stackCache.isNullOrBlank()) {
    gradle.beforeProject {
        val sub = path.trimStart(':').replace(':', '/')
        layout.buildDirectory.set(file(if (sub.isEmpty()) "$stackCache/probe-build/root" else "$stackCache/probe-build/$sub"))
    }
}

rootProject.name = "AndroidCliSmoke"
include(":app")
