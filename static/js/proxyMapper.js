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

        /*
         * constructionInstruction:
         *      .x -> raw x string
         *      .@label -> reference to another field
         *      .@@date -> index reference to another field
         *      .@>label -> reference to another field but direct set (do not append)
         */

        var ProxyMapper = function(mapping, constructionInstruction, data, options) {
            var that = this;
            this.itemsToBeMapped = Object.keys(constructionInstruction);
            this.constructionInstruction = constructionInstruction;
            this.mapping = mapping;

            //this.mapping = {
            //    dates: ["l", 0],
            //    index: {
            //        '@labels': [0],
            //        '@dates': [0]
            //    },
            //    //labels: ["l", 1, "l", 0],
            //    labels: [],
            //    //values: ["@dates,l", "{1}", "@labels,l", "{1}"]
            //    values: ["@dates,l", "{1}", "@labels"]
            //}



            this.data = data;

            this.result = {};

            var funcs = {};
            this.fillKey;
            this.labelKey = [];
            this.valueKey;
            this.itemsToBeMapped.forEach(function(item) {
                funcs[item] = new Function('value', 'datum', 'return value');
                let ci = constructionInstruction[item];

                if (ci.strategy !== undefined && ci.strategy == 'date') { // only 1 key can be a fill key
                    that.fillKey = item;
                }
                else if (ci.strategy !== undefined && ci.strategy == 'label') { // multiple keys can be label key
                    that.labelKey.push(item);
                }
                else if (ci.strategy !== undefined && ci.strategy == 'value') { // only 1 key can be value key
                    that.valueKey = item;
                }

                // init default type for wanted key
                let s = ci.instructions.split('.');
                if (s.length >= 2 && s[0] === '' && s[1] !== '') {
                    let p_res, p_key;
                    let c_res = that.result;
                    s.slice(1).forEach(function(k) {
                        if (k[0] === '@') {
                            return false;
                        }
                        c_res[k] = {};
                        p_res = c_res;
                        p_key = k;
                        c_res = c_res[k];
                    });
                    if (p_key !== undefined) {
                        p_res[p_key] = [];
                    }
                }
            });

            this._default_options = {
                fillValue: 0,
                functions: funcs,
                datum: false // the tree data to walk in parallel
            };
            this.options = $.extend({}, this._default_options, options);

            this.mappingI2 = {};
            this.mappingToIndexes = {};
            this.itemsToBeMapped.forEach(function(item) {
                that.mappingToIndexes[item] = {};
            });

            this.perform_mapping();
            return this.result;
        };
        
        ProxyMapper.prototype = {
            constructor: ProxyMapper,

            perform_mapping: function(data) {
                var that = this;
                var fk = this.fillKey;
                var lk = this.labelKey;
                var vk = this.valueKey;

                /* fill key is processed first */
                if (fk !== undefined && this.mapping[fk].length > 0) {
                    this.apply_strategy(fk);
                }

                // prepare fill array
                let fillArray = [];
                if (fk !== undefined) {
                    for (var i=0; i<this.result[fk].length; i++) {
                        if ((this.options.fillValue !== undefined && this.options.fillValue !== '')) {
                            fillArray.push(this.options.fillValue);
                        }
                    }
                }

                // inject prefill data
                for (let keyname in this.options.prefillData) {
                    let p_data = this.options.prefillData[keyname];
                    let subkeys = {};
                    subkeys[keyname] = p_data;
                    this.addFromInstruction(keyname, fillArray.slice(0), subkeys, true);
                    //this.i1_prefill = x;
                }

                // inject prefill data
                //for (var x of this.options.prefillData.labels) { 
                //    this.result[x] = fillArray.slice(0);
                //    this.i1_prefill = x;
                //}

                //if (this.mapping.labels.length > 0) {
                //    this.c_labels(this.data, this.mapping.labels); // probe and fetch all labels
                //}
                lk.forEach(function(labelK) {
                    if (that.mapping[labelK].length > 0) {
                        that.apply_strategy(labelK);
                    }
                });

                //if (Object.keys(this.result).length > 1 && this.mapping.values.length > 0) {
                //if (Object.keys(that.result).length > 0 && that.mapping[vk].length > 0) {
                //if (Object.keys(that.result).length > 1 && that.mapping[vk].length > 0) {
                if (Object.keys(that.result).length > 0 && that.mapping[vk].length > 0) {
                    that.apply_strategy(vk);
                    for (var k in that.result) { // filter out undefined value
                        let res = that.result[k];
                        if (res !== undefined && Array.isArray(res)) { // if object, picking is likely to be incoherent
                            let filtered = res.filter(function(n){ return n != undefined });
                            that.result[k] = filtered;
                        }
                    }
                }
            },


            apply_strategy: function(keyname) {
                let strategy = this.constructionInstruction[keyname].strategy;
                if (strategy == 'date') {
                    this.c_dates(this.data, this.mapping[keyname], keyname); // probe and fetch all dates
                } else if (strategy == 'label') {
                    this.c_labels(this.data, this.mapping[keyname], keyname); // probe and fetch all labels
                } else if (strategy == 'value') {
                    this.c_values(this.data, this.mapping[keyname], keyname); // fetch values and overwrite default values
                } else {
                    console.log('Invalid mapping strategy');
                }
            },

            c_dates: function(intermediate, instructions, keyname) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let index = instructions;
                    let val = intermediate[index];
                    if (that.mappingToIndexes[keyname][val] === undefined) {
                        //that.mappingToIndexes[keyname][val] = that.result['dates'].length;
                        that.mappingToIndexes[keyname][val] = that.result[keyname].length;
                        //let nval = that.options.functions.dates(val, additionalData.datum);
                        let nval = that.options.functions[keyname](val, additionalData.datum);
                        that.addFromInstruction(keyname, nval, {}, false);
                    }
                };
                this.iter(intermediate, instructions, matchingFun, { datum: this.options.datum });
            },
        
            c_labels: function(intermediate, instructions, keyname) {
                var that = this;
                var matchingFun = function (intermediate, instructions, additionalData) {
                    let reg = /\{(\w+)\}/;
                    let res = reg.exec(instructions);
                    if (res !== null) {
                        instructions = res[1];
                    }
                    let index = instructions;
                    if (index == 'l') { // labels are the keys themselves
                        for (let label in intermediate) {
                            let val = [];
                            for (var i=0; i<additionalData.valueLength; i++) {
                                if ((that.options.fillValue !== undefined && that.options.fillValue !== '')) {
                                    val.push(that.options.fillValue);
                                }
                            }
                            let nlabel = that.options.functions[keyname](label, additionalData.datum);
                            //that.result[nlabel] = val;
                            var subkeys = {};
                            subkeys[keyname] = nlabel;
                            that.addFromInstruction(keyname, val, subkeys, true);
                        }
                    } else {
                        let label = intermediate[index];
                        let val = [];
                        for (var i=0; i<additionalData.valueLength; i++) {
                            if ((that.options.fillValue !== undefined && that.options.fillValue != '')) {
                                val.push(that.options.fillValue);
                            }
                        }
                        let nlabel = that.options.functions[keyname](label, additionalData.datum);
                        var subkeys = {};
                        subkeys[keyname] = nlabel;
                        //that.result[nlabel] = val;
                        that.addFromInstruction(keyname, val, subkeys, true);
                    }
                };
                let valueLength = this.result[this.fillKey] !== undefined ? this.result[this.fillKey].length : 0;
                this.iter(intermediate, instructions, matchingFun, {valueLength: valueLength, datum: this.options.datum});
            },
        
            c_values: function(intermediate, instructions, keyname) {
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

                    let subkeyNames = that.get_subkeys_basename(keyname);
                    let subkeys = {};
                    let directValue = false;
                    subkeyNames.forEach(function(kn) {
                        // fetch index in array from the key
                        let v;
                        let kn_strip;
                        if (kn.substring(0, 2) === '@@') {
                            kn = kn.slice(1);
                            kn_strip = kn.slice(1);
                            v = additionalData[kn];
                            v = that.mappingToIndexes[kn_strip][v];
                            directValue = true;
                        } else {
                            if (kn.substring(0, 2) === '@>') {
                                kn = '@' + kn.slice(2);
                                directValue = true;
                            }
                            kn_strip = kn.slice(1);
                            v = additionalData[kn];
                            v = v !== undefined ? v : instructions;
                            // apply transformation function, only for non-index
                            v = that.options.functions[kn_strip](v, additionalData.datum);
                        }

                        subkeys[kn_strip] = v;
                    });

                    //that.options.functions.labels(i1, additionalData.datum);
                    //that.options.functions.values(val, additionalData.datum);

                    //let i1 = additionalData.i1;
                    ////i1 = i1 !== undefined ? i1 : that.i1_prefill;
                    //let i2 = additionalData.i2;
                    //// fetch index in array from the key
                    //let i2_adjusted = that.mappingI2[i2];

                    // fetch index in array from the key

                    // apply transformation function
                    //let ni1 = that.options.functions.labels(i1, additionalData.datum);
                    //let nval = that.options.functions.values(val, additionalData.datum);

                    //that.result[ni1][i2_adjusted] = nval;
                    //var subkeys = { labels: ni1, dates: i2_adjusted};

                    let nval = that.options.functions[keyname](val, additionalData.datum);
                    that.addFromInstruction(keyname, nval, subkeys, directValue);
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
                    if (record_inst[0] == '@') {
                        if (additionalData.mapping) {
                            flag_register_i = true;
                            i_type = record_inst;
                        }
                    }
                    //switch (record_inst) {
                    //    case 'i1':
                    //        if (additionalData.mapping) {
                    //            flag_register_i = true;
                    //            i_type = 'i1';
                    //        }
                    //        break;
                    //    case 'i2':
                    //        if (additionalData.mapping) {
                    //            flag_register_i = true;
                    //            i_type = 'i2';
                    //        }
                    //        break;
                    //    case '':
                    //        break;
                    //    default:
                    //        break;
                    //}

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

            addFromInstruction: function(constructionKey, value, subkeys, trueValue) {
                let inst = this.constructionInstruction[constructionKey].instructions;
                let split = inst.split('.').slice(1); // split and remove the first entry
                let cres = this.result;
                let p_res, p_key;
                split.forEach(function(inst) {
                    if (inst == '') {
                        return false;
                    } else if (inst[0] === '@') {
                        let subkeyName;
                        if (inst.substring(0, 2) === '@@' || inst.substring(0, 2) === '@>' ) {
                            subkeyName = inst.slice(2);
                        } else {
                            subkeyName = inst.slice(1);
                        }
                        let subkey = subkeys[subkeyName];
                        if (!cres.hasOwnProperty(subkey)) {
                            cres[subkey] = {};
                        }
                        p_res = cres;
                        p_key = subkey;
                        cres = cres[subkey];
                    } else {
                        p_res = cres;
                        p_key = inst;
                        cres = cres[inst];
                    }
                });

                //cres.push(value);
                //p_res[p_key].push(value);
                if (trueValue) {
                    p_res[p_key] = value;
                } else {
                    if (this.isObject(cres) && p_key !== undefined) {
                        p_res[p_key] = [];
                    }
                    p_res[p_key].push(value);
                }
            },

            get_subkeys_basename: function(keyname) {
                var list = [];
                let instructions = this.constructionInstruction[keyname].instructions.split('.');
                instructions = instructions.slice(1);
                instructions.forEach(function(inst) {
                    if (inst[0] === '@') {
                        list.push(inst);
                    }
                });
                return list;
            },
        
            isObject: function(v) {
                return v !== null && typeof v === 'object' && !Array.isArray(v);
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


