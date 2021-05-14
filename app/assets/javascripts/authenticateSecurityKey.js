(function (window) {
    "use strict";

    window.GOVUK.Modules.AuthenticateSecurityKey = function () {
        this.start = function (component) {
            $(component)
                .on('click', function (event) {
                    event.preventDefault();
                    console.log('pretend you just logged in okay');
                });
        };
    };
})(window);
