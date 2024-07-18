document.addEventListener('DOMContentLoaded', function() {
    const userLoggedIn = localStorage.getItem('loggedInUser');
    if (userLoggedIn) {
        fetchData(userLoggedIn);
    }
});

function loginUser(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    fetch('users.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').slice(1); // Skip the header row
            let validUser = false;
            rows.forEach(row => {
                const [csvUsername, csvPassword] = row.split(',');
                if (csvUsername === username && csvPassword === password) {
                    validUser = true;
                    localStorage.setItem('loggedInUser', csvUsername);
                    alert('Login successful!');
                    window.location.href = 'user_dashboard.html';
                }
            });
            if (!validUser) {
                alert('Invalid username or password.');
            }
        })
        .catch(error => {
            console.error('Error fetching the data:', error);
        });
}

function fetchData(username) {
    fetch('users.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').slice(1); // Skip the header row
            rows.forEach(row => {
                const columns = row.split(',');
                if (columns[0] === username) {
                    displayData(columns);
                }
            });
        })
        .catch(error => {
            console.error('Error fetching the data:', error);
        });
}

function displayData(columns) {
    document.getElementById('name').innerText = columns[7];
    document.getElementById('address').innerText = columns[8];
    document.getElementById('phone-number').innerText = columns[4];

    document.getElementById('vehicle-number').innerText = columns[2];
    document.getElementById('vehicle-rd-number').innerText = columns[3];
    document.getElementById('gps-id').innerText = columns[5];
    document.getElementById('vehicle-type').innerText = columns[9];
    document.getElementById('amount').innerText = columns[6];
}
// Function to log in an admin
function adminLogin(event) {
    event.preventDefault();
    const adminUsername = document.getElementById('admin-username').value;
    const adminPassword = document.getElementById('admin-password').value;

    fetch('admin.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n');
            for (const row of rows) {
                const [csvAdminUsername, csvAdminPassword] = row.split(',');
                if (csvAdminUsername === adminUsername && csvAdminPassword === adminPassword) {
                    alert('Admin login successful!');
                    localStorage.setItem('currentAdmin', adminUsername);
                    window.location.href = 'admin_dashboard.html';
                    return;
                }
            }
            alert('Invalid admin username or password.');
        });
}

function displayAdminDetails() {
    const adminUsername = localStorage.getItem('currentAdmin');
    document.getElementById('admin-username').innerText = adminUsername;

    fetch('users.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n');
            const userList = document.getElementById('user-list');
            userList.innerHTML = ''; // Clear previous list items
            rows.forEach(row => {
                const columns = row.split(',');
                if (columns.length === 10) { // Ensure all fields are present
                    const listItem = document.createElement('li');
                    listItem.innerHTML = `<div class="user-info">
                                              <p><strong>Username:</strong> ${columns[0]}</p>
                                              <p><strong>Name:</strong> ${columns[7]}</p>
                                              <p><strong>Address:</strong> ${columns[8]}</p>
                                              <p><strong>Phone Number:</strong> ${columns[4]}</p>
                                              <p><strong>Vehicle Number:</strong> ${columns[2]}</p>
                                              <p><strong>Vehicle RD Number:</strong> ${columns[3]}</p>
                                              <p><strong>GPS ID:</strong> ${columns[5]}</p>
                                              <p><strong>Vehicle Type:</strong> ${columns[9]}</p>
                                              <p><strong>Amount:</strong> ${columns[6]}</p>
                                          </div>`;
                    userList.appendChild(listItem);
                    fetchHistory(columns[2]); // Assuming vehicle ID is in the third column
                }
            });
        })
        .catch(error => {
            console.error('Error fetching user data:', error);
        });
}

if (document.getElementById('user-list')) {
    displayAdminDetails();
}

document.addEventListener('DOMContentLoaded', function() {
    const username = localStorage.getItem('currentUser');
    fetchData(username);
});

function fetchHistory(vehicleId) {
    const csvUrl = `${vehicleId}.csv`;

    fetch(csvUrl)
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').reverse(); // Reverse to show latest entries first
            const historyEntries = rows.map(row => {
                const [timestamp, location, distance, price] = row.split(',');
                return `<li>
                            <p><strong>Timestamp:</strong> ${timestamp}</p>
                            <p><strong>Location:</strong> ${location}</p>
                            <p><strong>Distance:</strong> ${distance}</p>
                            <p><strong>Price:</strong> ${price}</p>
                        </li>`;
            });
            document.getElementById('history-list').innerHTML = historyEntries.join('');
        })
        .catch(error => {
            console.error('Error fetching history:', error);
        });
}

// Function to calculate and display statistics
function displayStatistics(vehicleId) {
    const csvUrl = `${vehicleId}.csv`;

    fetch(csvUrl)
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').filter(row => row.trim() !== '');
            let totalPrice = 0;
            let totalDistance = 0;
            let travelCount = rows.length;

            rows.forEach(row => {
                const [timestamp, location, distance, price] = row.split(',');
                totalPrice += parseFloat(price);
                totalDistance += parseFloat(distance);
            });

            const avgPrice = (totalPrice / travelCount).toFixed(2);

            document.getElementById('total-travel-price').innerText = `Total Travel Price: ${totalPrice}`;
            document.getElementById('total-distance').innerText = `Total Distance: ${totalDistance}`;
            document.getElementById('avg-price').innerText = `Average Price: ${avgPrice}`;
            document.getElementById('travel-count').innerText = `Number of Travels: ${travelCount}`;

            // Create chart
            const ctx = document.getElementById('travelChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: rows.map((row, index) => `Travel ${index + 1}`),
                    datasets: [{
                        label: 'Price per Travel',
                        data: rows.map(row => parseFloat(row.split(',')[3])),
                        borderColor: '#354c7c',
                        backgroundColor: 'rgba(53, 76, 124, 0.2)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching statistics:', error);
        });
}


// Check if the current page is the admin dashboard and display admin details and user details
if (document.getElementById('user-list')) {
    displayAdminDetails();
}
document.addEventListener('DOMContentLoaded', function() {
    const username = localStorage.getItem('currentUser');
    fetchData(username);
});

function fetchData(username) {
    fetch('users.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n');
            for (const row of rows) {
                const columns = row.split(',');
                if (columns[0] === username) {
                    displayData(columns);
                    fetchHistory(columns[2]); // Assuming vehicle ID is in the third column
                    return;
                }
            }
        })
        .catch(error => {
            console.error('Error fetching the data:', error);
        });
}

function displayData(columns) {
    document.getElementById('name').innerText = columns[7];
    document.getElementById('address').innerText = columns[8];
    document.getElementById('phone-number').innerText = columns[4];
    document.getElementById('vehicle-number').innerText = columns[2];
    document.getElementById('vehicle-rd-number').innerText = columns[3];
    document.getElementById('gps-id').innerText = columns[5];
    document.getElementById('vehicle-type').innerText = columns[9];
    document.getElementById('amount').innerText = columns[6];
}

function fetchHistory(vehicleId) {
    const csvUrl = `${vehicleId}.csv`;

    fetch(csvUrl)
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').reverse(); // Reverse to show latest entries first
            const historyEntries = document.getElementById('history-entries');
            historyEntries.innerHTML = ''; // Clear previous data

            let totalTravelPrice = 0;
            let totalDistance = 0;
            let travelCount = 0;

            rows.forEach(row => {
                const columns = row.split(',');
                if (columns.length === 13) { // Ensure all fields are present
                    const entryBox = document.createElement('div');
                    entryBox.className = 'history-entry';
                    
                    entryBox.innerHTML = `
                        <p><strong>Timestamps:</strong> ${columns[0]}</p>
                        <p><strong>Start GPS:</strong> ${columns[1]}, ${columns[2]}</p>
                        <p><strong>End GPS:</strong> ${columns[3]}, ${columns[4]}</p>
                        <p><strong>Highway Distance:</strong> ${columns[5]}</p>
                        <p><strong>Avg Speed:</strong> ${columns[6]}</p>
                        <p><strong>Price by Distance:</strong> ${columns[7]}</p>
                        <p><strong>Price for Overspeed:</strong> ${columns[8]}</p>
                        <p><strong>Tax Price:</strong> ${columns[9]}</p>
                        <p><strong>Price for Peak Time:</strong> ${columns[10]}</p>
                        <p><strong>Price by Vehicle Type:</strong> ${columns[11]}</p>
                        <p><strong>Total Price:</strong> ${columns[12]}</p>
                    `;

                    historyEntries.appendChild(entryBox);

                    // Statistical Analysis
                    totalTravelPrice += parseFloat(columns[12]);
                    totalDistance += parseFloat(columns[5]);
                    travelCount++;
                }
            });

            const avgPrice = (totalTravelPrice / travelCount).toFixed(2);
            const avgdistance = (totalDistance / travelCount).toFixed(2);

            document.getElementById('total-travel-price').innerText = `Total Travel Price: ${totalTravelPrice}`;
            document.getElementById('total-distance').innerText = `Total Distance: ${totalDistance}`;
            document.getElementById('avg-price').innerText = `Average Price: ${avgPrice}`;
            document.getElementById('travel-count').innerText = `Number of Travels: ${travelCount}`;
           

            // Plot Graph (using Chart.js)
            const ctx = document.getElementById('travelChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from({ length: travelCount }, (_, i) => `Travel ${i + 1}`),
                    datasets: [{
                        label: 'Total Price per Travel',
                        data: rows.map(row => row.split(',')[12]),
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching the history data:', error);
        });
}

function plotGraphs(rows) {
    const totalPriceData = [];
    const timestamps = [];

    rows.forEach(row => {
        const columns = row.split(',');
        if (columns.length === 13) {
            timestamps.push(columns[0]);
            totalPriceData.push(parseFloat(columns[12]));
        }
    });

    // Using Chart.js to plot a bar chart
    const ctx = document.getElementById('priceChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: timestamps,
            datasets: [{
                label: 'Total Price',
                data: totalPriceData,
                backgroundColor: '#354c7c',
                borderColor: '#022954',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}
