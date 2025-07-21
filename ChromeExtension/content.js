(function () {
  const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");

  if (token) {
    console.log("Token found:", token);

    fetch("http://localhost:5000/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token })
    })
      .then(res => res.json())
      .then(data => {
        alert("Token sent to local script successfully!");
      })
      .catch(err => {
        alert("Error sending token: " + err);
      });
  } else {
    alert("Token not found in storage.");
  }
})();
