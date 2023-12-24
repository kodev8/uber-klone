"use strict";
var polyline = {};
function py2_round(e) {
    return Math.floor(Math.abs(e) + .5) * (e >= 0 ? 1 : -1)
}
function encode(e, o, n) {
    var r = (e = py2_round(e * n)) - (o = py2_round(o * n));
    r <<= 1,
    e - o < 0 && (r = ~r);
    for (var t = ""; r >= 32; )
        t += String.fromCharCode(63 + (32 | 31 & r)),
        r >>= 5;
    return t += String.fromCharCode(r + 63)
}
function flipped(e) {
    for (var o = [], n = 0; n < e.length; n++) {
        var r = e[n].slice();
        o.push([r[1], r[0]])
    }
    return o
}
polyline.decode = function(e, o) {
    for (var n, r = 0, t = 0, i = 0, l = [], u = 0, d = 0, p = null, c = Math.pow(10, Number.isInteger(o) ? o : 5); r < e.length; ) {
        p = null,
        u = 0,
        d = 0;
        do {
            d |= (31 & (p = e.charCodeAt(r++) - 63)) << u,
            u += 5
        } while (p >= 32);
        n = 1 & d ? ~(d >> 1) : d >> 1,
        u = d = 0;
        do {
            d |= (31 & (p = e.charCodeAt(r++) - 63)) << u,
            u += 5
        } while (p >= 32);
        t += n,
        i += 1 & d ? ~(d >> 1) : d >> 1,
        l.push([t / c, i / c])
    }
    return l
}
,
polyline.encode = function(e, o) {
    if (!e.length)
        return "";
    for (var n = Math.pow(10, Number.isInteger(o) ? o : 5), r = encode(e[0][0], 0, n) + encode(e[0][1], 0, n), t = 1; t < e.length; t++) {
        var i = e[t]
          , l = e[t - 1];
        r += encode(i[0], l[0], n),
        r += encode(i[1], l[1], n)
    }
    return r
}
,
polyline.fromGeoJSON = function(e, o) {
    if (e && "Feature" === e.type && (e = e.geometry),
    !e || "LineString" !== e.type)
        throw new Error("Input must be a GeoJSON LineString");
    return polyline.encode(flipped(e.coordinates), o)
}
,
polyline.toGeoJSON = function(e, o) {
    return {
        type: "LineString",
        coordinates: flipped(polyline.decode(e, o))
    }
}
,
"object" == typeof module && module.exports && (module.exports = polyline);