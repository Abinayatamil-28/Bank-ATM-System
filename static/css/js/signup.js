document.addEventListener("DOMContentLoaded", function() {
    var form = document.getElementById("signupForm");
    form.addEventListener("submit", function(event) {
        event.preventDefault(); // Prevent the default form submission

        var formData = new FormData(form);

        fetch(form.action, {
            method: form.method,
            body: formData
        })
        .then(response => {
            return response.json();
        })
        .then(data => {
            var notification = document.getElementById("notification");

            if (data.message.includes("successful")) {
                notification.innerText = "Signup successful. You can now login.";
                notification.style.backgroundColor = "#4CAF50"; // Green color for success
                form.reset(); // Clear the form fields
                setTimeout(function() {
                    notification.style.display = "none"; // Hide the notification after a delay
                }, 3000); // 3000 milliseconds = 3 seconds
            } else {
                notification.innerText = data.message;
                notification.style.backgroundColor = "#f44336"; // Red color for error
                notification.style.display = "block"; // Show the notification
            }
        })
        .catch(error => {
            console.error('Error:', error); // Log any errors to the console
            var notification = document.getElementById("notification");
            notification.innerText = "An error occurred. Please try again later.";
            notification.style.backgroundColor = "#f44336"; // Red color for error
            notification.style.display = "block"; // Show the notification
        });
    });
});
