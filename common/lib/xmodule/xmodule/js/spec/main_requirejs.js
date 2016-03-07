(function(requirejs) {
    requirejs.config({
        paths: {
            "moment": "xmodule/include/common_static/js/vendor/moment.min",
            "modernizr": "xmodule/include/common_static/edx-pattern-library/js/modernizr-custom",
            "afontgarde": "xmodule/include/common_static/edx-pattern-library/js/afontgarde",
            "edxicons": "xmodule/include/common_static/js/vendor/afontgarde/edx-icons",
            "draggabilly": "xmodule/include/common_static/js/vendor/draggabilly"
        },
        "moment": {
            exports: "moment"
        },
        "modernizr": {
            exports: "Modernizr"
        },
        "afontgarde": {
            exports: "AFontGarde"
        },
        "edxicons": {
            exports: "edxicons"
        },
        "draggabilly": {
            deps: ["jquery"],
            exports: "Draggabilly"
        }
    });

}).call(this, RequireJS.requirejs);
