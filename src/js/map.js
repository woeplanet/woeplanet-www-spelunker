if (!org) {
    var org = {};
}
if (!org.woeplanet) {
    org.woeplanet = {};
}

if (!org.woeplanet.map) {
    org.woeplanet.map = function () {
        this.maps = {
            'side': undefined,
            'main': undefined
        }
        this.ids = {
            'side': 'side-map',
            'main': 'main-map'
        }
        this.popup = undefined;
        this.banner_height = 0;
        this.banner_width = 0;
        this.min_map_height = 415;

        if (org.woeplanet.scale) {
            console.log('scale: ' + org.woeplanet.scale);
        }
        if (org.woeplanet.placetype) {
            console.log('placetype: ' + org.woeplanet.placetype);
        }

        // scale: 17, Suburb, zoom: 13
        // scale: 16, Town, zoom: 11
        // scale: 14, LocalAdmin, zoom: 10
        // scale: 9, County, zoom: 9
        // scale: 3, Ocean, zoom: 3
        // scale: 2, Continent: zoom: 3
        // scale: 1, Supername: zoom: 2

        if ($('#' + this.ids.side).length) {
            var options = {
                attributionControl: false,
                zoomControl: false,
                doubleClickZoom: false,
                boxZoom: false,
                dragging: false,
                keyboard: false,
                scrollWheelZoom: false,
                touchZoom: false
            };
            this.maps.side = L.map(this.ids.side, options);
            L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.{ext}', {
                minZoom: 0,
                maxZoom: 20,
                ext: 'png'
            }).addTo(this.maps.side);

            var attribution = '<a href="' + org.woeplanet.credits_url + '">Map Credits</a>';
            L.control.attribution({
                prefix: attribution,
                position: 'bottomleft'
            }).addTo(this.maps.side);

            // var self = this;
            // this.maps.side.on('zoomend', function() {
            //     console.log('zoom: ' + self.maps.side.getZoom());
            // });

            if (!$.isEmptyObject(org.woeplanet.bounds)) {
                console.log('set side map to bounds');
                this.maps.side.fitBounds(org.woeplanet.bounds);
            }
            else if (org.woeplanet.centroid) {
                console.log('set side map to centroid');
                this.maps.side.setView(org.woeplanet.centroid, org.woeplanet.zoom);
            }
            else {
                console.log('set side map to null island');
                var self = this;

                L.control.nullLabel({
                    position: 'topleft'
                }).addTo(this.maps.side);

                $.getJSON(org.woeplanet.nullisland_url, function (data) {
                    var myStyle = {
                        "color": "#ff7800",
                        "weight": 5,
                        "opacity": 0.65
                    };
                    var layer = L.geoJSON(data, {
                        style: myStyle
                    }).addTo(self.maps.side);
                    var bounds = layer.getBounds();
                    var point = bounds.getCenter();
                    var zoom = self.maps.side.getBoundsZoom(bounds, true);
                    zoom += 3;
                    self.maps.side.setView(point, zoom);
                });
            }
        }

        if ($('#' + this.ids.main).length) {
            var options = {
                attributionControl: false,
            };
            this.maps.main = L.map(this.ids.main, options);
            L.tileLayer('https://stamen-tiles-{s}.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}{r}.{ext}', {
                subdomains: 'abcd',
                minZoom: 0,
                maxZoom: 20,
                ext: 'png'
            }).addTo(this.maps.main);

            if (!$.isEmptyObject(org.woeplanet.bounds)) {
                console.log('set main map to bounds');
                this.maps.main.fitBounds(org.woeplanet.bounds);
                this.openPopup();
                this.syncMaps();
            }
            else if (org.woeplanet.centroid) {
                console.log('set main map to centroid');
                this.maps.main.setView(org.woeplanet.centroid, org.woeplanet.zoom);
                this.openPopup();
                this.syncMaps();
            }
            else {
                console.log('set main map to null island');

                var self = this;

                $.getJSON(org.woeplanet.nullisland_url, function (data) {
                    var layer = L.geoJSON(data).addTo(self.maps.main);
                    var bounds = layer.getBounds();
                    var point = bounds.getCenter();
                    var zoom = self.maps.main.getBoundsZoom(bounds, true);
                    zoom += 4;
                    self.maps.main.setView(point, zoom);
                    self.openPopup();
                    self.syncMaps();
                });
            }
        }
    };

    org.woeplanet.map.prototype.openPopup = function () {
        if ($('#' + this.ids.main).length && org.woeplanet.popup) {
            this.popup = L.popup({
                closeOnClick: false,
                closeButton: false,
            })
                .setContent(org.woeplanet.popup)
                .setLatLng(this.maps.main.getCenter())
                .openOn(this.maps.main);
        }
    }

    org.woeplanet.map.prototype.syncMaps = function () {
        if (!$.isEmptyObject(this.maps.main) && !$.isEmptyObject(this.maps.side)) {
            this.maps.main.on('zoomend', this.syncHandler.bind(this));
            this.maps.main.on('moveend', this.syncHandler.bind(this));
        }
    };

    org.woeplanet.map.prototype.syncHandler = function (_event) {
        var pt = this.maps.main.getCenter();
        var zm = this.maps.side.getZoom();
        this.maps.side.setView(pt, zm);
    };
}
