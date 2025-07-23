chrome.action.onClicked.addListener((tab) => {
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content.js"]
  });
});

// Listen for messages from content.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SHOW_REPORT_NOTIFICATION") {
    if (message.reportUrl) {
      // Extract the folder path from the URL (if you want to show it)
      const folderPath = "D:\\Shamanth_Krishna\\Other\\Keka Attendance Extractor\\Report"; // or get from server if you return it
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
