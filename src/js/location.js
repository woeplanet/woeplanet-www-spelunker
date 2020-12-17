$(function () {
    if ($('#location').length) {
        var lat = getParameterByName('lat');
        var lng = getParameterByName('lng');
        if (!lat && !lng) {
            if ('geolocation' in navigator) {
                navigator.geolocation.getCurrentPosition(geo_success, geo_error);
            }
            else {
                console.log('No navigator.geolocation');
            }
        }
    }

    function getParameterByName(name, url) {
        if (!url) url = window.location.href;
        name = name.replace(/[\[\]]/g, "\\$&");
        var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
            results = regex.exec(url);
        if (!results) return null;
        if (!results[2]) return '';
        return decodeURIComponent(results[2].replace(/\+/g, " "));
    }

    function geo_success(position) {
        $('#location-asking').toggle();
        $('#location-success').toggle();
        var params = {
            'lat': position.coords.latitude,
            'lng': position.coords.longitude
        }
        var qs = $.param(params);
        var redirect_to = window.location.href + '?' + qs;
        window.location.replace(redirect_to);
    }

    function geo_error(error) {
        console.log('Error: navigator.geolocation.getCurrentPosition() failed');
        $('#location-status').text(error.code + ' :' + error.message);
        $('#location-asking').toggle();
        $('#location-error').toggle();
    }
});
