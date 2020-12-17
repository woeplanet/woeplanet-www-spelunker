$.fn.resized = function (callback, timeout) {
    $(this).on('resize', function () {
        var self = $(this);
        if (self.data('resizeTimeout')) {
            clearTimeout(self.data('resizeTimeout'));
        }
        self.data('resizeTimeout', setTimeout(callback, timeout));
    });
};

// $('#search-info a').on('click', function (e) {
//     $('#search-query').toggle();
//     return false;
// });

// L.Control.nullLabel = L.Control.extend({
//     onAdd: function (_map) {
//         var text = L.DomUtil.create('div');
//         text.id = 'null-island';
//         text.className = 'text-panel';
//         text.innerHTML = '<p><strong>Ahem.</strong></p><p>We don\'t seem to have coordinates for this place.</p><p>So here\'s a map of Null Island instead.</p>';
//         return text;
//     },
//     onRemove: function (_map) { }
// });
// L.control.nullLabel = function (opts) {
//     return new L.Control.nullLabel(opts);
// }

// if (!org) {
//     var org = {};
// }
// if (!org.woeplanet) {
//     org.woeplanet = {};
// }

// if (!org.woeplanet.map) {
//     org.woeplanet.map = function() {
//         this.maps = {
//             'side': undefined,
//             'main': undefined
//         }
//         this.ids = {
//             'side': 'side-map',
//             'main': 'main-map'
//         }
//         this.popup = undefined;
//         this.banner_height = 0;
//         this.banner_width = 0;
//         this.min_map_height = 415;

//         if ($('#' + this.ids.side).length) {
//             var options = {
//                 attributionControl: false,
//                 zoomControl: false,
//                 doubleClickZoom: false,
//                 boxZoom: false,
//                 dragging: false,
//                 keyboard: false,
//                 scrollWheelZoom: false,
//                 touchZoom: false
//             };
//             this.maps.side = L.map(this.ids.side, options);
//             L.tileLayer('https://stamen-tiles-{s}.a.ssl.fastly.net/toner/{z}/{x}/{y}{r}.{ext}', {
//                 // attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
//                 subdomains: 'abcd',
//                 minZoom: 0,
//                 maxZoom: 20,
//                 ext: 'png'
//             }).addTo(this.maps.side);

//             var attribution = '<a href="' + org.woeplanet.credits_url + '">Map Credits</a>';
//             L.control.attribution({
//                 prefix: attribution
//             }).addTo(this.maps.side);


//             if (!$.isEmptyObject(org.woeplanet.bounds)) {
//                 console.log('set side map to bounds');
//                 this.maps.side.fitBounds(org.woeplanet.bounds);
//             }
//             else if (org.woeplanet.centroid) {
//                 console.log('set side map to centroid');
//                 this.maps.side.setView(org.woeplanet.centroid, org.woeplanet.zoom);
//             }
//             else {
//                 console.log('set side map to null island');
//                 var self = this;

//                 L.control.nullLabel({
//                     position: 'topleft'
//                 }).addTo(this.maps.side);

//                 $.getJSON(org.woeplanet.nullisland_url, function(data) {
//                     var myStyle = {
//                         "color": "#ff7800",
//                         "weight": 5,
//                         "opacity": 0.65
//                     };
//                     var layer = L.geoJSON(data, {
//                         style: myStyle
//                     }).addTo(self.maps.side);
//                     var bounds = layer.getBounds();
//                     var point = bounds.getCenter();
//                     var zoom = self.maps.side.getBoundsZoom(bounds, true);
//                     zoom +=3;
//                     self.maps.side.setView(point, zoom);
//                 });
//             }
//         }

//         // this.resizeHandler();
//         // $(window).resized(this.resizeHandler.bind(this), 300);

//         if ($('#' + this.ids.main).length) {
//             var options = {
//                 attributionControl: false,
//             };
//             this.maps.main = L.map(this.ids.main, options);
//             // L.tileLayer('https://{s}.tile.jawg.io/jawg-light/{z}/{x}/{y}{r}.png?access-token={accessToken}', {
//             //     minZoom: 0,
//             //     maxZoom: 22,
//             //     subdomains: 'abcd',
//             //     accessToken: 'XmFzpL9MZAb3JpT3sYHQfdWLt7vHVEqfphaDgpCtMHmdKodqCurdcER6oklotaAx'
//             // }).addTo(this.maps.main);
//             L.tileLayer('https://stamen-tiles-{s}.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}{r}.{ext}', {
//                 // attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
//                 subdomains: 'abcd',
//                 minZoom: 0,
//                 maxZoom: 20,
//                 ext: 'png'
//             }).addTo(this.maps.main);
//             // L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
//             //     // attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
//             //     subdomains: 'abcd',
//             //     maxZoom: 19
//             // }).addTo(this.maps.main);
//             // L.tileLayer('https://{s}.tile.jawg.io/jawg-dark/{z}/{x}/{y}{r}.png?access-token={accessToken}', {
//             //     // attribution: '<a href="http://jawg.io" title="Tiles Courtesy of Jawg Maps" target="_blank">&copy; <b>Jawg</b>Maps</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
//             //     minZoom: 0,
//             //     maxZoom: 22,
//             //     subdomains: 'abcd',
//             //     accessToken: 'XmFzpL9MZAb3JpT3sYHQfdWLt7vHVEqfphaDgpCtMHmdKodqCurdcER6oklotaAx'
//             // }).addTo(this.maps.main);
            

//             if (!$.isEmptyObject(org.woeplanet.bounds)) {
//                 console.log('set main map to bounds');
//                 this.maps.main.fitBounds(org.woeplanet.bounds);
//                 this.openPopup();
//                 this.syncMaps();
//             }
//             else if (org.woeplanet.centroid) {
//                 console.log('set main map to centroid');
//                 this.maps.main.setView(org.woeplanet.centroid, org.woeplanet.zoom);
//                 this.openPopup();
//                 this.syncMaps();
//             }
//             else {
//                 console.log('set main map to null island');

//                 var self = this;

//                 $.getJSON(org.woeplanet.nullisland_url, function (data) {
//                     var layer = L.geoJSON(data).addTo(self.maps.main);
//                     var bounds = layer.getBounds();
//                     var point = bounds.getCenter();
//                     var zoom = self.maps.main.getBoundsZoom(bounds, true);
//                     zoom += 4;
//                     self.maps.main.setView(point, zoom);
//                     self.openPopup();
//                     self.syncMaps();
//                 });
//             }
//         }
//     };

//     org.woeplanet.map.prototype.openPopup = function() {
//         if ($('#' + this.ids.main).length && org.woeplanet.popup) {
//             this.popup = L.popup({
//                 closeOnClick: false,
//                 closeButton: false,
//             })
//                 .setContent(org.woeplanet.popup)
//                 .setLatLng(this.maps.main.getCenter())
//                 .openOn(this.maps.main);
//         }
//     }

//     org.woeplanet.map.prototype.syncMaps = function() {
//         if (!$.isEmptyObject(this.maps.main) && !$.isEmptyObject(this.maps.side)) {
//             this.maps.main.on('zoomend', this.syncHandler.bind(this));
//             this.maps.main.on('moveend', this.syncHandler.bind(this));
//         }
//     };

//     org.woeplanet.map.prototype.syncHandler = function (_event) {
//         var pt = this.maps.main.getCenter();
//         var zm = this.maps.side.getZoom();
//         this.maps.side.setView(pt, zm);
//     };

//     org.woeplanet.map.prototype.getBannerHeight = function() {
//         this.banner_height = $('.page-banner').height();
//         this.banner_width = $('.page-banner').width();
//     }

//     org.woeplanet.map.prototype.resizeHandler = function() {
//         this.getBannerHeight();

//         if ($('#main-map').length || $('#side-map').length) {
//             if ($(window).width() >= this.banner_height) {
//                 if ($('#main-map').length) {
//                     $('#main-map').css('height', ($(window).height() - this.banner_height));
//                     $('#main-map').css('width', this.banner_width);
//                 }
//                 if ($('#side-map').length) {
//                     $('#side-map').css('height', $(window).height());
//                 }
//                 if (!$.isEmptyObject(this.maps.main)) {
//                     this.maps.main.invalidateSize();
//                 }
//                 if (!$.isEmptyObject(this.maps.side)) {
//                     this.maps.side.invalidateSize();
//                 }
//             }
//             else {
//                 if ($(window).height() <= this.min_map_height) {
//                     if ($('#main-map').length) {
//                         $('#main-map').css('height', this.min_map_height);
//                         $('#main-map').css('width', this.banner_width);
//                     }
//                     if ($('#side-map').length) {
//                         $('#side-map').css('height', $(window).height());
//                     }
//                     if (!$.isEmptyObject(this.maps.main)) {
//                         this.maps.main.invalidateSize();
//                     }
//                     if (!$.isEmptyObject(this.maps.side)) {
//                         this.maps.side.invalidateSize();
//                     }
//                 }
//                 else {
//                     if ($('#main-map').length) {
//                         $('#main-map').css('height', ($(window).height() - this.banner_height));
//                         $('#main-map').css('width', this.banner_width);
//                     }
//                     if ($('#side-map').length) {
//                         $('#side-map').css('height', $(window).height());
//                     }
//                     if (!$.isEmptyObject(this.maps.main)) {
//                         this.maps.main.invalidateSize();
//                     }
//                     if (!$.isEmptyObject(this.maps.side)) {
//                         this.maps.side.invalidateSize();
//                     }
//                 }
//             }
//         }
//     }
// }

// $(function () {
//     if ($('#location').length) {
//         var lat = getParameterByName('lat');
//         var lng = getParameterByName('lng');
//         if (!lat && !lng) {
//             if ('geolocation' in navigator) {
//                 navigator.geolocation.getCurrentPosition(geo_success, geo_error);
//             }
//             else {
//                 console.log('No navigator.geolocation');
//             }
//         }
//     }

//     function getParameterByName(name, url) {
//         if (!url) url = window.location.href;
//         name = name.replace(/[\[\]]/g, "\\$&");
//         var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
//             results = regex.exec(url);
//         if (!results) return null;
//         if (!results[2]) return '';
//         return decodeURIComponent(results[2].replace(/\+/g, " "));
//     }

//     function geo_success(position) {
//         $('#location-asking').toggle();
//         $('#location-success').toggle();
//         var params = {
//             'lat': position.coords.latitude,
//             'lng': position.coords.longitude
//         }
//         var qs = $.param(params);
//         var redirect_to = window.location.href + '?' + qs;
//         window.location.replace(redirect_to);
//     }

//     function geo_error(error) {
//         console.log('Error: navigator.geolocation.getCurrentPosition() failed');
//         $('#location-error').text(error.code + ' :' + error.message);
//         $('#location-asking').toggle();
//         $('#location-error').toggle();
//     }
// });
