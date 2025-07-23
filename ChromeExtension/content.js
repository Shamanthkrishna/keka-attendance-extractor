(function () {
  const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");

  if (token) {
    fetch("http://localhost:5000/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token })
    })
      .then(res => res.json())
      .then(data => {
        console.log("Server response:", data);
        // Send a message to the background script with the report URL
        chrome.runtime.sendMessage({
          type: "SHOW_REPORT_NOTIFICATION",
          reportUrl: data.report_url
        });
      })
      .catch(err => {
        chrome.runtime.sendMessage({
          type: "SHOW_REPORT_NOTIFICATION",
          reportUrl: null,
          error: err.toString()
        });
      });
  } else {
    chrome.runtime.sendMessage({
      type: "SHOW_REPORT_NOTIFICATION",
      reportUrl: null,
      error: "Token not found in storage."
    });
  }
})();
