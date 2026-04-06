const map = new ol.Map({
    target: 'map',
    layers: [
        new ol.layer.Tile({
            source: new ol.source.OSM(),
        }),
    ],
    view: new ol.View({
        center: [0, 0],
        zoom: 2,
        projection: 'EPSG:4326'
    }),
});

const tileLayer = new ol.layer.Tile({
    source: new ol.source.TileWMS({
        url: 'http://localhost:8080/geoserver/practise/wms',
        params: { 'LAYERS': '', 'TILED': true },
        serverType: 'geoserver',
        // Must match the map view projection
        projection: 'EPSG:4326',
    }),
});

let selectedTable = '';

const getLayerAttributes = (event) => {
    console.log(event.target.value);
    map.removeLayer(tileLayer);
    selectedTable = event.target.value;

    const myHeaders = new Headers();
    myHeaders.append("Content-Type", "application/json");

    const raw = JSON.stringify({
        "schema_name": "dynamic_sld",
        "table_name": `${event.target.value}`
    });

    const requestOptions = {
        method: "POST",
        headers: myHeaders,
        body: raw,
        redirect: "follow"
    };

    fetch("http://localhost:8000/api/get-columns", requestOptions)
        .then((response) => response.json())
        .then((result) => renderAttributes(result))
        .catch((error) => console.error(error));

    const newParams = {
        'LAYERS': `practise:${event.target.value}`,
        'TILED': true,
        'CQL_FILTER': null
    };
    tileLayer.getSource().updateParams(newParams);
    map.addLayer(tileLayer);
};

const renderAttributes = (columns) => {
    const attrList = document.querySelector('.attr-list');
    attrList.innerHTML = columns.map(col => `
        <div class="attr-item">
            <span class="attr-dot" data-type="${col.data_type}"></span>
            ${col.column_name}
        </div>
    `).join('');
};

const filterLayer = () => {
    console.log(selectedTable);
    let addedCriteria = document.getElementById('criteriaText').value;
    console.log(addedCriteria);

    const myHeaders = new Headers();
    myHeaders.append("Content-Type", "application/json");

    const raw = JSON.stringify({
        "table_name": `${selectedTable}`,
        "text": `${addedCriteria}`
    });

    console.log(raw);

    const requestOptions = {
        method: "POST",
        headers: myHeaders,
        body: raw,
        redirect: "follow"
    };

    fetch("http://localhost:8000/api/generate-sql", requestOptions)
        .then((response) => response.json())
        .then((result) => {
            console.log(result);
            map.removeLayer(tileLayer);
            let params = {
                'LAYERS': `practise:${selectedTable}`,
                'TILED': true,
                'CQL_FILTER': result.sql
            };
            console.log(params);
            tileLayer.getSource().updateParams(params);
            map.addLayer(tileLayer);
        })
        .catch((error) => console.error(error));
};

// ── GetFeatureInfo on click ──
map.on('singleclick', function (evt) {
    // Guard: only query if a layer is actually loaded
    if (!selectedTable) return;

    const view = map.getView();
    const viewResolution = view.getResolution();
    const projection = view.getProjection(); // EPSG:4326 — matches tileLayer source

    const url = tileLayer.getSource().getFeatureInfoUrl(
        evt.coordinate,
        viewResolution,
        projection,          // ✅ use the actual map projection, not hardcoded 3857
        {
            'INFO_FORMAT': 'application/json',
            'FEATURE_COUNT': 10
        }
    );

    if (!url) return;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            const infoEl = document.getElementById('info');
            const bodyEl = document.getElementById('info-body');
            infoEl.classList.add('visible');

            if (!data.features || data.features.length === 0) {
                bodyEl.innerHTML = '<span style="color:#6b7280;font-size:0.8rem;">No feature found at this location.</span>';
                return;
            }

            bodyEl.innerHTML = data.features.map((feature, i) => {
                const props = feature.properties;
                const rows = Object.entries(props)
                    .map(([key, val]) => `
                        <tr>
                            <td class="info-key">${key}</td>
                            <td class="info-val">${val ?? '—'}</td>
                        </tr>`)
                    .join('');
                return `
                    <div class="info-feature">
                        <div class="info-feature-title">Feature ${i + 1}</div>
                        <table class="info-table">${rows}</table>
                    </div>`;
            }).join('');
        })
        .catch(err => {
            console.error('GetFeatureInfo error:', err);
            const infoEl = document.getElementById('info');
            const bodyEl = document.getElementById('info-body');
            infoEl.classList.add('visible');
            bodyEl.innerHTML = '<span style="color:#ef4444;font-size:0.8rem;">Error fetching feature info.</span>';
        });
});