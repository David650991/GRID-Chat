document.addEventListener('DOMContentLoaded', () => {
    // Admin Panel Toggle
    const adminBtn = document.getElementById('toggleAdminBtn');
    if(adminBtn) {
        adminBtn.addEventListener('click', () => {
            document.getElementById('adminPanel').classList.toggle('hidden');
        });
    }

    // Any other dashboard logic
});
