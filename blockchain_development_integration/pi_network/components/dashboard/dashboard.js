// dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Example: Fetch data from an API and display it on the dashboard
    fetchData();

    // Event listener for a button click
    const refreshButton = document.getElementById('refreshButton');
    refreshButton.addEventListener('click', fetchData);
});

function fetchData() {
    // Simulate fetching data from an API
    console.log('Fetching data...');

    // Example data
    const data = [
        { id: 1, name: 'Loan Application 1', status: 'Pending' },
        { id: 2, name: 'Loan Application 2', status: 'Approved' },
        { id: 3, name: 'Loan Application 3', status: 'Rejected' }
    ];

    displayData(data);
}

function displayData(data) {
    const dataContainer = document.getElementById('dataContainer');
    dataContainer.replaceChildren(); // Clear previous data

    data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        const title = document.createElement('h2');
        title.textContent = item.name;
        const status = document.createElement('p');
        status.textContent = `Status: ${item.status}`;
        card.append(title, status);
        dataContainer.appendChild(card);
    });
}
