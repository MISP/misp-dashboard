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
            console.log(options);
            this._default_options = {
                fillValue: 0,
                functions: {
                    dates: function (value) {return value;},
                    labels: function (value) {return value;},
                    values: function (value) {return value;}
                }
            };
            this.options = $.extend({}, this._default_options, options);
            this.result = {};

            this.result.dates = [];

            this.mappingI2 = {};
            this.perform_mapping();
            return this.result;
        };
        
        ProxyMapper.prototype = {
            constructor: ProxyMapper,

            perform_mapping: function(data) {
                if (this.mapping.dates.length > 0) {
                    this.c_dates(this.data, this.mapping.dates); // probe and fetch all dates
                }
                if (this.mapping.labels.length > 0) {
                    this.c_labels(this.data, this.mapping.labels); // probe and fetch all labels
                }
                if (this.mapping.labels.length > 0 && this.mapping.values.length > 0) {
                    this.c_values(this.data, this.mapping.values); // fetch values and overwrite default values
                    for (var k in this.result) {
                        this.result[k] = this.result[k].filter(function(n){ return n != undefined });
                    }
                }
            },
        
            c_dates: function(intermediate, instructions) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    let val = intermediate[index];
                    if (that.mappingI2[val] === undefined) {
                        that.mappingI2[val] = that.result['dates'].length;
                        let nval = that.options.functions.dates(val);
                        that.result['dates'].push(nval);
                    }
                };
                this.iter(intermediate, instructions, matchingFun, {});
            },
        
            c_labels: function(intermediate, instructions, valuesLength) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    if (index == 'l') { // labels are the key themself
                        for (let label in intermediate) {
                            let val = [];
                            for (var i=0; i<additionalData.valueLength; i++) {
                                if ((that.options.fillValue !== undefined && that.options.fillValue != '')) {
                                    val.push(that.options.fillValue);
                                }
                            }
                            let nval = that.options.functions.dates(val);
                            that.result[label] = nval;
                        }
                    } else {
                        let label = intermediate[index];
                        let val = [];
                        for (var i=0; i<additionalData.valueLength; i++) {
                            if ((that.options.fillValue !== undefined && that.options.fillValue != '')) {
                                val.push(that.options.fillValue);
                            }
                        }
                        let nlabel = that.options.functions.labels(label);
                        that.result[nlabel] = val;
                    }
                };
                this.iter(intermediate, instructions, matchingFun, {valueLength: this.result.dates.length});
            },
        
            c_values: function(intermediate, instructions) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    let val = intermediate[index];
                    let i1 = additionalData.i1;
                    let i2 = additionalData.i2;
                    let i2_adjusted = that.mappingI2[i2];
                    let ni1 = that.options.functions.labels(i1);
                    let nval = that.options.functions.values(val);
                    that.result[ni1][i2_adjusted] = nval;
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
        
                var flag_register_i = false;
                var i_type;
                if (instructions.length == 1) {
                    matchingFun(intermediate, instructions[0], additionalData);
                } else {
                    switch (instructions[0]) {
                        case 'i1':
                            if (additionalData.mapping) {
                                flag_register_i = true;
                                i_type = 'i1';
                            }
                            break;
                        case 'i2':
                            if (additionalData.mapping) {
                                flag_register_i = true;
                                i_type = 'i2';
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
                        if (flag_register_i) {
                            let sub_instructions = additionalData.mapping.index[i_type]
                            let curI;
                            if (sub_instructions.length > 0) {
                                curI = this.fetch_value(node, sub_instructions);
                            } else {
                                console.log('Should never happend');
                            }
                            additionalData[i_type] = curI;
                        }
                        this.iter(node, instructions.slice(1), matchingFun, additionalData);
                    }
                } else if (this.isObject(intermediate)) {
                    for (var k in intermediate) {
                        var node = intermediate[k];
                        if (flag_register_i) {
                            let sub_instructions = additionalData.mapping.index[i_type]
                            let curI;
                            if (sub_instructions.length > 0) {
                                curI = this.fetch_value(node, sub_instructions);
                            } else {
                                curI = k;
                            }
                            additionalData[i_type] = curI;
                        }
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


