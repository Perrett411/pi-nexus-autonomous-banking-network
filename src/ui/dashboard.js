// dashboard.js

class Dashboard {
    constructor(userId) {
        this.userId = userId;
        this.transactionHistory = [];
        this.accountBalance = 0;
        this.init();
    }

    // Initialize the dashboard
    init() {
        this.render();
        this.fetchTransactionHistory();
        this.updateAccountBalance();
    }

    // Fetch transaction history (mock data)
    fetchTransactionHistory() {
        // In a real application, this would be an API call
        this.transactionHistory = [
            { id: 1, amount: 200, date: '2023-10-01', type: 'credit' },
            { id: 2, amount: 150, date: '2023-10-02', type: 'debit' },
            { id: 3, amount: 300, date: '2023-10-03', type: 'credit' },
        ];
        this.renderTransactionHistory();
    }

    // Update account balance (mock data)
    updateAccountBalance() {
        // In a real application, this would be an API call
        this.accountBalance = 1000; // Example balance
        this.renderAccountBalance();
    }

    // Render the dashboard
    render() {
        const dashboardContainer = document.createElement('div');
        dashboardContainer.id = 'dashboard';
        const heading = document.createElement('h1');
        heading.textContent = 'User Dashboard';
        const balanceDiv = document.createElement('div');
        balanceDiv.id = 'account-balance';
        const historyHeading = document.createElement('h2');
        historyHeading.textContent = 'Transaction History';
        const historyList = document.createElement('ul');
        historyList.id = 'transaction-history';
        dashboardContainer.append(heading, balanceDiv, historyHeading, historyList);
        document.body.appendChild(dashboardContainer);
    }

    // Render account balance
    renderAccountBalance() {
        const balanceElement = document.getElementById('account-balance');
        balanceElement.replaceChildren();
        const strong = document.createElement('strong');
        strong.textContent = `Account Balance: $${this.accountBalance}`;
        balanceElement.appendChild(strong);
    }

    // Render transaction history
    renderTransactionHistory() {
        const historyElement = document.getElementById('transaction-history');
        historyElement.replaceChildren();
        this.transactionHistory.forEach(tx => {
            const li = document.createElement('li');
            li.textContent = `${tx.date}: $${tx.amount} (${tx.type})`;
            historyElement.appendChild(li);
        });
    }
}

// Example usage
const userId = 'user123';
const userDashboard = new Dashboard(userId);

export default Dashboard;
