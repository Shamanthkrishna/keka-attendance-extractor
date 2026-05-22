// ---------------------------------------------------------------------------
// Auto-extract alarm: fires every weekday at 18:30 local time
// ---------------------------------------------------------------------------
const ALARM_NAME = "kekaAutoExtract";
const TRIGGER_HOUR = 18;
const TRIGGER_MINUTE = 30;

function scheduleNextAlarm() {
  const now = new Date();
  const next = new Date(now);
  next.setSeconds(0, 0);
  next.setHours(TRIGGER_HOUR, TRIGGER_MINUTE);
  if (next <= now) {
    next.setDate(next.getDate() + 1);        // already past today's trigger → tomorrow
  }
  // Skip to Monday if the next trigger falls on a weekend
  const day = next.getDay();                 // 0=Sun, 6=Sat
  if (day === 0) next.setDate(next.getDate() + 1);
  if (day === 6) next.setDate(next.getDate() + 2);

  chrome.alarms.create(ALARM_NAME, { when: next.getTime(), periodInMinutes: 24 * 60 });
  console.log("[Keka] Next auto-extract scheduled for", next.toLocaleString());
}

// Set up alarm on install/update/Chrome start
chrome.runtime.onInstalled.addListener(scheduleNextAlarm);
chrome.runtime.onStartup.addListener(scheduleNextAlarm);

// ---------------------------------------------------------------------------
// Alarm handler: find Keka tab → inject content.js → extract token
// ---------------------------------------------------------------------------
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;

  const now = new Date();
  const dow = now.getDay();
  if (dow === 0 || dow === 6) {
    console.log("[Keka] Weekend — skipping auto-extract.");
    return;
  }
  console.log("[Keka] Alarm fired — searching for Keka tab...");

  const tabs = await chrome.tabs.query({ url: "*://*.keka.com/*" });
  if (!tabs.length) {
    console.warn("[Keka] No Keka tab found. Open keka.com and the extension will extract on next trigger.");
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon.png",
      title: "Keka Auto-Extract Skipped",
      message: "No Keka tab is open. Open Keka in Chrome and it will run next time."
    });
    return;
  }

  chrome.scripting.executeScript({
    target: { tabId: tabs[0].id },
    files: ["content.js"]
  });
});

// ---------------------------------------------------------------------------
// Manual button click (original behaviour — kept for on-demand use)
// ---------------------------------------------------------------------------
chrome.action.onClicked.addListener((tab) => {
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content.js"]
  });
});

// ---------------------------------------------------------------------------
// Listen for messages from content.js (notification display)
// ---------------------------------------------------------------------------
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SHOW_REPORT_NOTIFICATION") {
    if (message.reportUrl) {
      const folderPath = "D:\\Shamanth_Krishna\\Other\\Keka Attendance Extractor\\Report";
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Attendance Extraction Complete",
        message: "Report folder:\n" + folderPath
      });
    } else {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: "Attendance Extraction Failed",
        message: message.error || "Unknown error occurred."
      });
    }
  }
});

