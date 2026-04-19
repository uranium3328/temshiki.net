// Авто-скрытие flash сообщений
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Превью изображения при загрузке
    document.querySelectorAll('input[type="file"][accept*="image"]').forEach(function (input) {
        input.addEventListener('change', function () {
            const file = this.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function (e) {
                let preview = input.parentElement.querySelector('.img-preview');
                if (!preview) {
                    preview = document.createElement('img');
                    preview.className = 'img-preview rounded-2 mt-2';
                    preview.style.maxHeight = '120px';
                    preview.style.maxWidth = '100%';
                    input.parentElement.appendChild(preview);
                }
                preview.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    });
});
