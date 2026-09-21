(function ($) {
    $(document).ready(function () {
        $('.pq').click(function () {
            $('html, body').animate({scrollTop: $("#question_" + $(this).data('q')).offset().top - 70}, 300)
        });
        if ($('body').hasClass('start-test')) {
            document.addEventListener('contextmenu', function (e) {
                e.preventDefault();
            });

            document.addEventListener('selectstart', function (e) {
                e.preventDefault();
            });

            document.addEventListener('copy', function (e) {
                e.preventDefault();
            });

            document.addEventListener('keydown', function (e) {
                if (
                    (e.ctrlKey && e.key === 'u') || // Ctrl+U – kodni ko‘rish
                    (e.ctrlKey && e.shiftKey && e.key === 'I') || // DevTools
                    (e.ctrlKey && e.key === 'c') // Ctrl+C
                ) {
                    e.preventDefault();
                }
            });
        }
    })
})(jQuery);