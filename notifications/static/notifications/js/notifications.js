// notifications/static/notifications/js/notifications.js
document.addEventListener('DOMContentLoaded', function () {
    const notificationBellDropdown = document.getElementById('notificationBellDropdown'); 
    const notificationBadge = document.getElementById('notificationBadge');
    const notificationList = document.getElementById('notificationList');
    const noNotificationsMessageContainer = document.getElementById('noNotificationsMessageContainer');

    const expiryToggle = document.getElementById('expiryNotificationsToggle');
    const lowStockToggle = document.getElementById('lowStockNotificationsToggle');

    function loadNotificationSettings() {
        if (expiryToggle) {
            expiryToggle.checked = localStorage.getItem('expiryNotificationsEnabled') === 'true';
        }
        if (lowStockToggle) {
            lowStockToggle.checked = localStorage.getItem('lowStockNotificationsEnabled') === 'true';
        }
    }

    function saveNotificationSettings() {
        if (expiryToggle) {
            localStorage.setItem('expiryNotificationsEnabled', expiryToggle.checked);
        }
        if (lowStockToggle) {
            localStorage.setItem('lowStockNotificationsEnabled', lowStockToggle.checked);
        }
        // After saving settings, re-fetch/re-filter notifications
        fetchCachedNotifications(); 
    }

    if (expiryToggle) expiryToggle.addEventListener('change', saveNotificationSettings);
    if (lowStockToggle) lowStockToggle.addEventListener('change', saveNotificationSettings);
    // Load settings on init, true by default if not set
    if (localStorage.getItem('expiryNotificationsEnabled') === null && expiryToggle) {
        localStorage.setItem('expiryNotificationsEnabled', 'true');
    }
    if (localStorage.getItem('lowStockNotificationsEnabled') === null && lowStockToggle) {
        localStorage.setItem('lowStockNotificationsEnabled', 'true');
    }
    if (expiryToggle || lowStockToggle) loadNotificationSettings();
    
    let activeNotifications = []; 
    let notificationSocket = null;
    let shakeTimeout = null;

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    async function fetchCachedNotifications() {
        if (!notificationBellDropdown) return;

        try {
            const url = (typeof NOTIFICATIONS_URLS !== 'undefined' && NOTIFICATIONS_URLS.getCached) 
                        ? NOTIFICATIONS_URLS.getCached 
                        : "/notifications/get-cached/"; // Fallback if global var not set
            
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!response.ok) {
                console.error("Failed to fetch cached notifications:", response.status, response.statusText);
                activeNotifications = []; 
                renderNotifications();
                return;
            }
            const notificationsFromServer = await response.json();
            activeNotifications = []; 

            notificationsFromServer.forEach(notif => {
                const expiryEnabled = localStorage.getItem('expiryNotificationsEnabled') === 'true';
                const lowStockEnabled = localStorage.getItem('lowStockNotificationsEnabled') === 'true';
                let shouldAdd = false;
                if ((notif.reason === 'Expiring Soon' || notif.reason === 'Expired') && expiryEnabled) {
                    shouldAdd = true;
                }
                if (notif.reason === 'Low Stock' && lowStockEnabled) {
                    shouldAdd = true;
                }
                if (shouldAdd) {
                    if (!activeNotifications.find(n => n.id === notif.id)) {
                        activeNotifications.push(notif);
                    }
                }
            });
            activeNotifications.sort((a, b) => parseFloat(b.id.split('_').pop()) - parseFloat(a.id.split('_').pop()));
            renderNotifications();
        } catch (error) {
            console.error("Error fetching cached notifications:", error);
            activeNotifications = [];
            renderNotifications();
        }
    }

    function connectWebSocket() {
        const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
        notificationSocket = new WebSocket(
            wsScheme + '://' + window.location.host + '/ws/notifications/'
        );

        notificationSocket.onopen = function(e) { console.log("Notification WebSocket connected"); };

        notificationSocket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.type === 'new_notification') {
                const notification = data.notification;
                const expiryEnabled = localStorage.getItem('expiryNotificationsEnabled') === 'true';
                const lowStockEnabled = localStorage.getItem('lowStockNotificationsEnabled') === 'true';
                let shouldShow = false;
                if ((notification.reason === 'Expiring Soon' || notification.reason === 'Expired') && expiryEnabled) shouldShow = true;
                if (notification.reason === 'Low Stock' && lowStockEnabled) shouldShow = true;
                
                if (shouldShow) {
                    if (!activeNotifications.find(n => n.id === notification.id)) {
                        activeNotifications.push(notification);
                        activeNotifications.sort((a, b) => parseFloat(b.id.split('_').pop()) - parseFloat(a.id.split('_').pop()));
                        renderNotifications(); 
                    }
                }
            }
        };
        notificationSocket.onclose = function (e) {
            console.error('Notification WebSocket closed. Reconnecting in 5 seconds...');
            setTimeout(connectWebSocket, 5000);
        };
        notificationSocket.onerror = function(err) {
            console.error('Notification WebSocket error:', err.message, 'Closing socket');
            if (notificationSocket) notificationSocket.close();
        };
    }

    async function handleDismissClick(notificationId) {
        const originalNotifications = [...activeNotifications];
        activeNotifications = activeNotifications.filter(n => n.id !== notificationId);
        renderNotifications();

        try {
            const urlBase = (typeof NOTIFICATIONS_URLS !== 'undefined' && NOTIFICATIONS_URLS.dismissNotificationBase) 
                            ? NOTIFICATIONS_URLS.dismissNotificationBase
                            : "/notifications/dismiss/0/"; // Fallback
            const dismissUrl = urlBase.replace('0', notificationId);

            const response = await fetch(dismissUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: `Server error: ${response.status}` }));
                throw new Error(errorData.message || `Server error: ${response.status}`);
            }
            const result = await response.json();
            if (result.status !== 'success') {
                throw new Error(result.message || "Failed to dismiss on server");
            }
            // console.log("Notification dismissed successfully on server.");
        } catch (error) {
            console.error("Error dismissing notification:", error.message);
            activeNotifications = originalNotifications;
            renderNotifications();
            // Optionally show a user-facing error message, e.g., using SweetAlert or a simple alert
            // alert("Could not dismiss notification: " + error.message);
        }
    }

    function renderNotifications() {
        if (!notificationList || !notificationBadge || !notificationBellDropdown || !noNotificationsMessageContainer) return;
        
        notificationList.innerHTML = ''; 

        if (activeNotifications.length > 0) {
            notificationBadge.textContent = activeNotifications.length;
            notificationBadge.style.display = 'inline-block';
            if (notificationBellDropdown) { 
                notificationBellDropdown.classList.remove('shake');
                void notificationBellDropdown.offsetWidth; 
                requestAnimationFrame(() => { notificationBellDropdown.classList.add('shake'); });
                if (shakeTimeout) clearTimeout(shakeTimeout);
                shakeTimeout = setTimeout(() => { if (notificationBellDropdown) notificationBellDropdown.classList.remove('shake'); }, 700);
            }
            noNotificationsMessageContainer.style.display = 'none';

            activeNotifications.forEach(notif => {
                const listItem = document.createElement('li');
                listItem.className = 'notification-item'; 
                listItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong class="notification-reason">${notif.reason}</strong>
                            <span class="notification-message">${notif.message}</span>
                        </div>
                        <button class="btn-close btn-sm ms-2 notification-dismiss" data-id="${notif.id}" aria-label="Dismiss"></button>
                    </div>
                `;
                notificationList.appendChild(listItem);
            });

            document.querySelectorAll('.notification-dismiss').forEach(button => {
                button.addEventListener('click', function (event) {
                    event.stopPropagation();
                    handleDismissClick(this.dataset.id);
                });
            });

        } else {
            notificationBadge.style.display = 'none';
            if (notificationBellDropdown) notificationBellDropdown.classList.remove('shake');
            noNotificationsMessageContainer.style.display = 'block';
        }
    }
    
    if (notificationBellDropdown) { 
        fetchCachedNotifications(); 
        connectWebSocket();
    } else {
        // console.log("Notification bell not found on this page. WS and cache fetch skipped.");
    }
});