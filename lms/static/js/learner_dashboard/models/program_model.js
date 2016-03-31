/**
 * Model for Course Programs.
 */
(function (define) {
    'use strict';
    define([
            'backbone'
        ], 
        function (Backbone) {
        return Backbone.Model.extend({
            initialize: function(data) {
                if (data){
                    this.set({
                        name: data.name,
                        category: data.category,
                        subtitle: data.subtitle,
                        organizations: data.organizations,
                        marketingUrl: data.marketing_url,
                        smallBannerUrl: data.banner_image_urls.w348h116,
                        mediumBannerUrl: data.banner_image_urls.w435h145,
                        largeBannerUrl: data.banner_image_urls.w726h242,
                        breakpoints: {
                            max: {
                                small: '348px',
                                medium: '768px',
                                large: '980px'
                            }
                        }
                    });
                }
            }
        });
    });
}).call(this, define || RequireJS.define);
