(function keepAliveLoop() {
    const keepAlive = () => {
        fetch('/keep-alive') // Replace with your server's endpoint
            .then(response => {
                if (response.ok) {
                    console.log('Keep-alive ping sent successfully.');
                } else {
                    console.error('Keep-alive ping failed with status:', response.status);
                }
            })
            .catch(error => console.error('Error sending keep-alive ping:', error));
    };

    // Send the first request immediately
    keepAlive();

    // Repeat every 5 minutes (adjust interval as needed)
    setInterval(keepAlive, 1 * 60 * 1000); // 5 minutes in milliseconds
})();