function initMap(interactive=true) {
    // console.log(document.querySelector('#map-container' ), window.map)
    // if (document.querySelector('#map-container' ) && window.map) {
    //     console.log('Map Already initialized', window.map)
    //     return
    // }

    locationiq.key = 'pk.7cdd1ae3d1720c0eecdf58cfb5e74172';
    var mapStyleUrlPrefix = 'https://tiles.locationiq.com/v3';
    function getMapStyleURL(type, theme) {
    return mapStyleUrlPrefix + "/" + theme + "/" + type + '.json?key=' + locationiq.key;
}
    //Define the map and configure the map's theme
        var map = new maplibregl.Map({
            container: 'map-container',
            style: getMapStyleURL('vector', 'light'),
            zoom: 12,
            center: [2.3627963138153443, 48.81569448188089,] // centered on epita
        });

        var nav = new maplibregl.NavigationControl();
        map.addControl(nav, 'top-right');

        // //Add a 'full screen' button to the map
        // map.addControl(new maplibregl.FullscreenControl());
                
        //Add a Scale to the map
        map.addControl(new maplibregl.ScaleControl({
            maxWidth: 80,
            unit: 'metric' //imperial for miles
        }));

        //Add Geolocation control to the map (will only render when page is opened over HTTPS)
        map.addControl(new maplibregl.GeolocateControl({    
            positionOptions: {
                enableHighAccuracy: true
            },
            trackUserLocation: true
    }));


    const parser = new DOMParser();
    document.addEventListener('setMapWidth', (evt) => {
        let mc = document.getElementById("map-container");
        mc.classList.remove('lg:col-span-6', 'lg:col-span-8');
        let newWidth = evt.detail.width;
        if (newWidth === 'grow'){
            mc.classList.add('lg:col-span-8');
        }else{
            mc.classList.add('lg:col-span-6');
        }
    })

    const pinPickupSvgString = '<svg xmlns="http://www.w3.org/2000/svg"  width="32" height="32" viewBox="0 0 32 32" fill="none"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 23c6.075 0 11-4.925 11-11S18.075 1 12 1 1 5.925 1 12s4.925 11 11 11Zm0-8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" fill="currentColor"></path></svg>'
    const pinPickupSvg = parser.parseFromString(
    pinPickupSvgString,
    "image/svg+xml",
    ).documentElement;


    const pinDropoffSvgString  = '<svg xmlns="http://www.w3.org/2000/svg"  width="32" height="32" viewBox="0 0 32 32" fill="none"><path fill-rule="evenodd" clip-rule="evenodd" d="M22 2H2v20h20V2Zm-7 7H9v6h6V9Z" fill="currentColor"></path></svg>'
    const pinDropoffSvg = parser.parseFromString(
    pinDropoffSvgString,
    "image/svg+xml",
    ).documentElement;

    
    let markers= {
        pickup: null,
        dropoff: null
    };

    let listeners = []

    const iconStyles = {
        pickup: pinPickupSvg,
        dropoff: pinDropoffSvg
    }
    
    window.map = map
    window.markers = markers
    window.listeners = listeners
    window.iconStyles = iconStyles

    if(!interactive) return

    initMapListener('pickup')



}

function getcoords(coord_type, lat_lon_osm_id)  {

    if (!markers[coord_type]?.coords || !markers[coord_type].osm_id) return 

    if (lat_lon_osm_id === "lat"){
        return marker = markers[coord_type].coords[0]
    }else if (lat_lon_osm_id == "lon") {
        return marker = markers[coord_type].coords[1]
    } else if (lat_lon_osm_id == "osm_id") {
        return markers[coord_type].osm_id
    }else{
        return 
    }
}

function fitMapToBounds(geojson) {
var coordinates = geojson.coordinates;
var bounds = coordinates.reduce(function(bounds, coord) {
    return bounds.extend(coord);
}, new maplibregl.LngLatBounds(coordinates[0],coordinates[0]));
map.fitBounds(bounds, {
    padding: 50,
    duration: 1
});
}

function flyTo(lat, lon, zoom) {
map.flyTo({
    center: [lon, lat],
    zoom: zoom
});
}


function addRouteToMap(geojsonString) {

    var mapLayer = map.getLayer('route');
    if (typeof mapLayer !== 'undefined') {
        map.removeLayer('route').removeSource('route');
    }
    map.addSource('route', {
        'type': 'geojson',
        'data': {
            'type': 'Feature',
            'properties': {},
            'geometry': geojsonString
        }
    });
    map.addLayer({
        'id': 'route',
        'type': 'line',
        'source': 'route',
        'layout': {
            'line-join': 'round',
            'line-cap': 'round'
        },
        'paint': {
            'line-color': '#ff3a41',
            'line-width': 3
        }
    });
    fitMapToBounds(geojsonString);
}


function getGeoJsonStringFromResponse(geometry, geometriesFormat) {
switch (geometriesFormat) {
case 'geojson':
    return geometry;
case 'polyline6':
    return polyline.toGeoJSON(geometry, 6);
case 'polyline':
default:
    return polyline.toGeoJSON(geometry);
}
}


function processRoutingResponse(data) {
    // check if dom is ready
    allSubmitters = document.querySelectorAll('.form-submitter')
    allSubmitters.forEach(submitter => {
        // console.log('disableing', submitter)
        submitter.disabled = true
    })
    if (!data) return
    response = data
    // console.log('inprocess', data)
    var geometryString = response.geometry;
    // console.log(geometryString)
    let geometriesFormat = 'polyline'
    var geojsonString = getGeoJsonStringFromResponse(geometryString, geometriesFormat)
    // addMarkersToTheMapForRouting();
    addRouteToMap(geojsonString);

    allSubmitters.forEach(submitter => {
        submitter.disabled = false
        // console.log('enabling', submitter)
    })
}


function getPickupDetails() {
    return document.querySelector('#pickup_details')?.value
}

function drawRoute(evt) {
    let { elt, ...params} = evt.detail
    console.log(evt.detail)
    let url = '/locations/route-data?' + new URLSearchParams({...params})
    fetch(url, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'HX-Request': 'true', //TOOD: create validation middleware

        }
    
    })
    .then(response => response.json())
    .then(data => processRoutingResponse(data))
    .catch(err => console.log(err))
}

function createMarker (lat, lon, osm_id, markerType) {

    const latF = parseFloat(lat)
    const lonF = parseFloat(lon)

    if (isNaN(latF) || isNaN(lonF) || !osm_id || !markerType) {
        return;
    }
    
     // remove any previous marker of the given type
    // remove map from dom
    markers[markerType] = null;
    document.querySelector(`#marker-${markerType}`)?.remove();

    // console.log(markerType, 'fsdfjsdjf')

    var marker = document.createElement('div');
    marker.id = `marker-${markerType}`;
    marker.insertAdjacentElement('beforeend', iconStyles[markerType]);
    marker.classList.add('marker');

    // add marker to map
    new maplibregl.Marker(marker)
        .setLngLat([lonF, latF])
        .addTo(map);

    markers[markerType] = {
        element: marker, 
        coords: [latF, lonF],
        osm_id: osm_id
    }


        
}

function handleAfterCreateMarker (lat, lon) {

    const pickupMarkerPosition = markers.pickup?.coords;
    const dropoffMarkerPosition = markers.dropoff?.coords;

    // console.log(pickupMarkerPosition, dropoffMarkerPosition)

    let formSubmitter = document.querySelector('.form-submitter')
    // reverse to lon lat
    if (pickupMarkerPosition && dropoffMarkerPosition) {

        if(formSubmitter) formSubmitter.disabled=false
        // reverse to lon lat format for maplibregl
        map.fitBounds([
        pickupMarkerPosition.slice().reverse(),
        dropoffMarkerPosition.slice().reverse(),
    ], {
            padding: 20,
            duration: 0
        });
    }else {
       if(formSubmitter) formSubmitter.disabled=true

        flyTo(lat, lon, 10);
    }
}

function createMarkerFromElement (element) {

    const lat = element.dataset.lat;
    const lon = element.dataset.lon;
    const osm_id = element.dataset.osm_id;
    // console.log(lat, lon, osm_id)
    const title = element.querySelector(".title").textContent;
    const markerType = element.dataset.type;

    if (isNaN(lat) || isNaN(lon) || !title || title.trim() === "") {
        return;
    }

    createMarker(lat, lon, osm_id, markerType)

    // get both marker positions and fit in map
    handleAfterCreateMarker(lat, lon)

    let triggerInput = element.closest('.results-wrapper').querySelector("input");
    triggerInput.value = title;
    triggerInput.focus();

    // clear the search results
    element.parentElement.innerHTML = "";
     // hide map clickers
     document.querySelectorAll('.map-clicker').forEach(clicker => {
        clicker.classList.add('hidden')
        clicker.classList.remove('flex')
    })

}

function fetchAndDraw (pickup_data, dropoff_data) {

    let searchParams = new URLSearchParams({
        'pickup_lat':pickup_data.lat,
        'pickup_lon' :pickup_data.lon ,
        'pickup_osm_id':pickup_data.osm_id,
        'dropoff_lat':dropoff_data.lat,
        'dropoff_lon':dropoff_data.lon,
        'dropoff_osm_id':dropoff_data.osm_id,
    })

    fetch('/locations/route-data?' + searchParams, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'HX-Request': true,
        },
    
    })
        .then(response => response.json())
        .then(data => {
            // console.log(data)
            processRoutingResponse(data)
            createMarker(pickup_data.lat, pickup_data.lon, pickup_data.osm_id , "pickup")
            createMarker(dropoff_data.lat, dropoff_data.lon, dropoff_data.osm_id , "dropoff")
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function showMapClicker(evt, markerType) {
    if (evt.detail.isError) return
    let mapClicker = document.querySelector(`#${markerType}-set-location-on-map`)
    mapClicker.classList.remove('hidden')
    mapClicker.classList.add('flex')
}

function initMapListener(markerType) {

    if (markerType !== 'pickup' && markerType !== 'dropoff') return

    listeners.forEach(listener => {
        map.off('click', listener)
    })

    

     // hide map clickers
     document.querySelectorAll('.map-clicker').forEach(clicker => {
        clicker.classList.add('hidden')
        clicker.classList.remove('flex')
    })

    // close result containers
    document.querySelectorAll('.results-container').forEach(elt => {
        elt.innerHTML = ""
    })

    listeners = []


    function mapClickHandler(e) {
        
            listeners.push(this)
    
            // console.log(e.lngLat);
            fetch('/locations/reverse-geocode?' + new URLSearchParams({
                'lat': e.lngLat.lat,
                'lon': e.lngLat.lng,
            }), {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'HX-Request': true,
                },
            })
                .then(response => response.json())
                .then(data => {
                    // console.log(data)
                    createMarker(e.lngLat.lat, e.lngLat.lng, data.osm_id , markerType)
                    document.querySelector(`#${markerType}`).value = data.display_name
                    handleAfterCreateMarker(e.lngLat.lat, e.lngLat.lng)

                    // show clear icon
                document.querySelector(`#${markerType}-set-location-on-map`).closest('results-wrapper')
                .querySelector('clear-icon').classList.remove('invsible')
                
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
        };
    
    map.on('click', mapClickHandler)
    listeners.push(mapClickHandler)
}

function fetchAndDrawFromElt(elt) {
    let data = elt.querySelector('data')
    let pickup_data ={
        lat: data.dataset.pickup_lat,
        lon: data.dataset.pickup_lon,
        osm_id: data.dataset.pickup_osm_id
    }
    let dropoff_data = {
        lat: data.dataset.dropoff_lat,
        lon: data.dataset.dropoff_lon,
        osm_id: data.dataset.dropoff_osm_id
    }
    fetchAndDraw(pickup_data, dropoff_data)
}

function clearMap() {
    // Remove all markers
    // Remove 'route' layer
    var routeLayer = map.getLayer('route');
    if (typeof routeLayer !== 'undefined') {
        map.removeLayer('route').removeSource('route');
    }

    // Remove all markers
    document.querySelectorAll('.marker').forEach(marker => {
        marker.remove()
    })


}
  