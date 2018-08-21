(function(factory) {
        "use strict";
        if (typeof define === 'function' && define.amd) {
            define(['jquery'], factory);
        } else if (window.jQuery && !window.jQuery.fn.ProxyMapper) {
            factory(window.jQuery);
        }
    }
    (function($) {
        'use strict';

        var ProxyMapper = function(mapping, data, options) {
            this.mapping = mapping;
            this.data = data;
            this._default_options = {
                fillValue: 0
            };
            this.options = $.extend({}, this._default_options, options);
            //this.result = {
            //    dates: [],
            //};
            this.result = {};

            //for (var k in this.mapping) {
            //    this.result[k] = [];
            //}
            this.result.dates = [];

            this.mappingDate = {};
            this.perform_mapping();
            return this.result;
        };
        
        ProxyMapper.prototype = {
            constructor: ProxyMapper,

            perform_mapping: function(data) {
                console.log(this.mapping);
                if (this.mapping.dates.length > 0) {
                    this.c_dates(this.data, this.mapping.dates); // probe and fetch all dates
                }
                if (this.mapping.labels.length > 0) {
                    this.c_labels(this.data, this.mapping.labels); // probe and fetch all labels
                }
                if (this.mapping.labels.length > 0 && this.mapping.values.length > 0) {
                    this.c_values(this.data, this.mapping.labels); // fetch values and overwrite default values
                }
            },
        
            c_dates: function(intermediate, instructions) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    let val = intermediate[index];
                    that.mappingDate[val] = that.result['dates'].length;
                    that.result['dates'].push(val);
                };
                this.iter(intermediate, instructions, matchingFun, {});
            },
        
            c_labels: function(intermediate, instructions, valuesLength) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    let label = intermediate[index];
                    let val = [];
                    for (var i=0; i<additionalData.valueLength; i++) {
                        val.push(that.options.fillValue);
                    }
                    that.result[label] = val;
                };
                this.iter(intermediate, instructions, matchingFun, {valueLength: this.result.dates.length});
            },
        
            c_values: function(intermediate, instructions) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    let label = intermediate[index];
                    let val = that.fetch_value(intermediate, additionalData.mapping.values);
                    let curDateIndex = that.mappingDate[additionalData.curDate];
                    that.result[label][curDateIndex] = val;
                };
                this.iter(intermediate, instructions, matchingFun, {mapping: this.mapping});
            },
        
            // deterministic function, always follow the indexes
            fetch_value: function(intermediate, instructions) {
                if (instructions.length == 0) {
                    return intermediate;
                } else {
                    let index = instructions[0];
                    return this.fetch_value(intermediate[index], instructions.slice(1));
                }
            },
        
            iter: function(intermediate, instructions, matchingFun, additionalData) {
                if (instructions === undefined || instructions.length == 0) {
                    return;
                }
        
                var flag_register_date = false;
                if (instructions.length == 1) {
                    matchingFun(intermediate, instructions[0], additionalData);
                } else {
                    switch (instructions[0]) {
                        case 'd':
                            if (additionalData.mapping) {
                                flag_register_date = true;
                            }
                            break;
                        case 'l':
                            break;
                        case '':
                            break;
                        default:
                            break;
                    }
                }
        
                if (!(Array.isArray(intermediate) || this.isObject(intermediate))) {
                    return;
                }
        
                if (Array.isArray(intermediate)) {
                    for (var node of intermediate) {
                        if (flag_register_date) {
                            let curDate = this.fetch_value(node, additionalData.mapping.dateFromNode);
                            additionalData.curDate = curDate;
                        }
                        this.iter(node, instructions.slice(1), matchingFun, additionalData);
                    }
                } else if (this.isObject(intermediate)) {
                    for (var k in intermediate) {
                        if (flag_register_date) {
                            let curDate = this.fetch_value(node, additionalData.mapping.dateFromNode);
                            additionalData.curDate = curDate;
                        }
                        var node = intermediate[k];
                        this.iter(node, instructions.slice(1), matchingFun, additionalData);
                    }
                }
            },
        
            isObject: function(v) {
                return v !== null && typeof v === 'object';
            }
        };

        $.proxyMapper = ProxyMapper;
        $.fn.proxyMapper = function(options) {
            var pickerArgs = arguments;

            return this.each(function() {
                var $this = $(this),
                    inst = $this.data('proxyMapper'),
                    options = ((typeof option === 'object') ? option : {});
                if ((!inst) && (typeof option !== 'string')) {
                    $this.data('proxyMapper', new ProxyMapper($this, options));
                } else {
                    if (typeof option === 'string') {
                        inst[option].apply(inst, Array.prototype.slice.call(pickerArgs, 1));
                    }
                }
            });
        }
        $.fn.proxyMapper.constructor = ProxyMapper;
    })
);


