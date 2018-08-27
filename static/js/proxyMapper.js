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
                fillValue: 0,
                functions: {
                    dates: function (value, datum) {return value;},
                    labels: function (value, datum) {return value;},
                    values: function (value, datum) {return value;}
                },
                prefillData: {
                    dates: [],
                    labels: []
                },
                datum: false // the tree data to walk in parallel
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
                    for (var x of this.options.prefillData.dates) { this.result['dates'].push(x); }
                    this.c_dates(this.data, this.mapping.dates); // probe and fetch all dates
                }

                let fillArray = [];
                for (var i=0; i<this.result.dates.length; i++) {
                    if ((this.options.fillValue !== undefined && this.options.fillValue !== '')) {
                        fillArray.push(this.options.fillValue);
                    }
                }
                for (var x of this.options.prefillData.labels) { 
                    this.result[x] = fillArray.slice(0);
                    this.i1_prefill = x;
                }
                if (this.mapping.labels.length > 0) {
                    this.c_labels(this.data, this.mapping.labels); // probe and fetch all labels
                }

                //if (this.mapping.labels.length > 0 && this.mapping.values.length > 0) {
                if (Object.keys(this.result).length > 1 && this.mapping.values.length > 0) {
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
                        let nval = that.options.functions.dates(val, additionalData.datum);
                        that.result['dates'].push(nval);
                    }
                };
                this.iter(intermediate, instructions, matchingFun, { datum: this.options.datum });
            },
        
            c_labels: function(intermediate, instructions, valuesLength) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let reg = /\{(\w+)\}/;
                    let res = reg.exec(instructions);
                    if (res !== null) {
                        instructions = res[1];
                    }
                    let index = instructions;
                    if (index == 'l') { // labels are the keys themself
                        for (let label in intermediate) {
                            let val = [];
                            for (var i=0; i<additionalData.valueLength; i++) {
                                if ((that.options.fillValue !== undefined && that.options.fillValue !== '')) {
                                    val.push(that.options.fillValue);
                                }
                            }
                            let nlabel = that.options.functions.labels(label, additionalData.datum);
                            that.result[nlabel] = val;
                        }
                    } else {
                        let label = intermediate[index];
                        let val = [];
                        for (var i=0; i<additionalData.valueLength; i++) {
                            if ((that.options.fillValue !== undefined && that.options.fillValue != '')) {
                                val.push(that.options.fillValue);
                            }
                        }
                        let nlabel = that.options.functions.labels(label, additionalData.datum);
                        that.result[nlabel] = val;
                    }
                };
                this.iter(intermediate, instructions, matchingFun, {valueLength: this.result.dates.length, datum: this.options.datum});
            },
        
            c_values: function(intermediate, instructions) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let val;
                    if (!instructions) { // value is self (intermediate)
                        val = intermediate;
                    } else {
                        let reg = /\{(\w+)\}/;
                        let res = reg.exec(instructions);
                        if (res !== null) {
                            instructions = res[1];
                        }
                        let index = instructions;
                        val = intermediate[index];
                    }
                    let i1 = additionalData.i1;
                    i1 = i1 !== undefined ? i1 : that.i1_prefill;
                    let i2 = additionalData.i2;
                    let i2_adjusted = that.mappingI2[i2];
                    let ni1 = that.options.functions.labels(i1, additionalData.datum);
                    let nval = that.options.functions.values(val, additionalData.datum);
                    that.result[ni1][i2_adjusted] = nval;
                };
                this.iter(intermediate, instructions, matchingFun, {mapping: this.mapping, datum: this.options.datum});
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
                if (instructions === undefined) {
                    return;
                }
                if (instructions.length == 0 || instructions[0] === '') {
                    return matchingFun(intermediate, false, additionalData);
                }
        
                var flag_register_i = false;
                var i_type;
                if (instructions.length == 1) {
                    return matchingFun(intermediate, instructions[0], additionalData);
                } else {
                    let tmp = new String(instructions[0]).split(',');
                    let record_inst = tmp[0]
                    let ind_inst = tmp.length == 2 ? tmp[1] : tmp[0];
                    switch (record_inst) {
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
                        case '':
                            break;
                        default:
                            break;
                    }

                    let inst = ind_inst;
                    let reg = /\{(\w+)\}/;
                    let res = reg.exec(inst);
                    if (res !== null) { // check if index requested
                        let i = res[1];
                        if (flag_register_i) {
                            let sub_instructions = additionalData.mapping.index[i_type]
                            let curI;
                            if (sub_instructions.length > 0) {
                                curI = this.fetch_value(intermediate[i], sub_instructions);
                            } else {
                                curI = i;
                            }
                            additionalData[i_type] = curI;
                        }
                        additionalData.datum = this.update_datum(additionalData.datum, i);
                        return this.iter(intermediate[i], instructions.slice(1), matchingFun, additionalData);
                    }
                    // fallback to standard loop

                }
        
                if (!(Array.isArray(intermediate) || this.isObject(intermediate))) {
                    return;
                }
        
                if (Array.isArray(intermediate)) {
                    for (var k=0; k<intermediate.length; k++) {
                        var node = intermediate[k];
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
                        // update datum object
                        additionalData.datum = this.update_datum(additionalData.datum, k);
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
                        additionalData.datum = this.update_datum(additionalData.datum, k, true);
                        this.iter(node, instructions.slice(1), matchingFun, additionalData);
                    }
                }
            },
        
            isObject: function(v) {
                return v !== null && typeof v === 'object';
            },

            update_datum: function(d, k, should_look_into_linkname) {
                if (!d) { // no datum, ignoring update
                    return;
                } else if (d.children == undefined) {
                    return d;
                }
                var next;
                if (should_look_into_linkname) {
                    for (var n in d.children) {
                        var c = d.children[n];
                        if (c.linkname == k) {
                            next = c;
                            break;
                        }
                    }
                } else {
                    next = d.children[k];
                }
                return next;
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


