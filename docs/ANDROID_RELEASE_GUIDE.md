# PCOS360 — Android Release & Physical Device QA Guide

## 1. Release APK Artifact Details

- **File Path**: `mobile/android/app/build/outputs/apk/release/app-release.apk`
- **File Size**: `84,492,315 bytes (~80.6 MB)`
- **Build Type**: Production Release (Hermes JS Engine, R8 Code Shrinking, Resource Optimization)
- **Minimum Android Version**: Android 7.0 (API 24)
- **Target Android Version**: Android 16 (API 36)
- **Default Cloud API Endpoint**: `https://pcos360-backend.onrender.com/api`

---

## 2. Installation on Physical Android Handsets

### Method A: Over USB via Android Debug Bridge (ADB)

1. Enable **Developer Options** and **USB Debugging** on your Android handset:
   - Go to **Settings > About Phone**.
   - Tap **Build Number** 7 times until developer options are unlocked.
   - Go to **Settings > System > Developer Options** and enable **USB Debugging**.
2. Connect the phone to your workstation via USB.
3. Confirm connection:
   ```bash
   adb devices
   ```
   (Accept the "Allow USB debugging" prompt on your handset if prompted).
4. Install the release APK:
   ```bash
   adb install -r mobile/android/app/build/outputs/apk/release/app-release.apk
   ```

### Method B: Direct APK Side-loading

1. Copy `app-release.apk` to your phone via Google Drive, WhatsApp, or USB File Transfer.
2. On your Android device, tap the APK file in **Files** or **Downloads**.
3. If prompted, select **Allow from this source** to permit sideloading.
4. Tap **Install** and then **Open**.

---

## 3. Physical Device QA Checklist

Execute the following verification steps on the handset:

| Step | Verification Action | Expected Outcome | Pass/Fail |
| :--- | :--- | :--- | :--- |
| **1. First Launch** | Open PCOS360 from app launcher. | App boots into Welcome / Sign In screen smoothly; no crash. | [ ] |
| **2. Registration** | Register with a new email and password. | JWT session created, automatically enters onboarding / profile screen. | [ ] |
| **3. Health Profile** | Fill age, height, weight, PCOS diagnosis status. | Profile saved to PostgreSQL; calculated BMI displayed. | [ ] |
| **4. Cycle Tracking** | Log 3 completed cycles with start/end dates. | Cycle cards reflect history; rhythm classification updates. | [ ] |
| **5. Daily Check-in** | Log daily symptoms and lifestyle metrics (sleep, stress, water, exercise). | Record persists to database; timestamp updates. | [ ] |
| **6. Lab Biomarkers**| Enter Fasting Glucose and Total Testosterone lab reports. | Values categorized as Normal/Elevated with reference ranges. | [ ] |
| **7. PCOSCOPE** | Open PCOSCOPE tab; select 7-day and 30-day windows. | Rhythm status, symptom curves, and Pearson correlation render. | [ ] |
| **8. AI Health Chat**| Ask a health question in the AI Chat tab. | Gemini responds with grounded patient context in < 6 seconds. | [ ] |
| **9. Copilot** | Generate Doctor Consultation Packet. | Structured clinical notes and targeted doctor questions appear. | [ ] |
| **10. Disconnect QA**| Turn on Airplane Mode and navigate screens. | Graceful offline notice appears without crashing the application. | [ ] |
| **11. Session Test** | Close and re-open app from recent apps tray. | User remains signed in via persisted secure token. | [ ] |
| **12. Sign Out** | Tap Profile > Log Out. | Session revoked server-side; app returns to Welcome screen. | [ ] |

---

## 4. Rebuilding the Release APK

If changes are made to the mobile source code:

```bash
cd mobile/android
./gradlew assembleRelease --no-daemon
```
The new signed binary will be generated at `mobile/android/app/build/outputs/apk/release/app-release.apk`.

