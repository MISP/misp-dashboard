(function(factory) {
        "use strict";
        if (typeof define === 'function' && define.amd) {
            define(['jquery'], factory);
        } else if (window.jQuery && !window.jQuery.fn.TreeFromJson) {
            factory(window.jQuery);
        }
    }
    (function($) {
        'use strict';

        var TreeFromJson = function(container, data, options) {
            this.container = container;
            this._default_options = {
                margin: {top: 20, right: 20, bottom: 20, left: 20},
                width: container.width() > 800 ? container.width()/2-32 : 800,
                height: container.height() > 800 ? container.height()/2 : 800,
                treeNodes : {
                    width: 3,
                    depth: 5
                },
                maxCharDisplay: 20,
                itemColors: ['#337ab7', '#5cb85c', '#d9534f', '#f0ad4e', '#d9edf7', '#dff0d8', '#f2dede', '#fcf8e3'],
                duration: 500,
                interaction: true,
                default_function: '    return value;',
                toBeMapped: {},
                toBeMappedList: []
            };
            this.options = $.extend({}, this._default_options, options);

            this.data = data;
            this.treeData = [this.generate_d3_tree_from_json(data, '', this.options.treeNodes.depth, this.options.treeNodes.depth, this.options.treeNodes.width)];

            this._letterWidth = 8; // width to estimate the width space taken by a letter
            this.width = this.options.width - this.options.margin.right - this.options.margin.left,
            this.height = this.options.height - this.options.margin.top - this.options.margin.bottom;

            this.treeDiv = $('<div class="treeDiv panel panel-default panel-body"></div>');
            this.treeDiv.css('max-width', this.options.width+this.options.margin.left+this.options.margin.right-10+'px');
            this.container.append(
                $('<div class="treeContainer"></div>').append(this.treeDiv)
            );

            this.itemColors = new Map(); // the map from item to color
            this.mappingDomTable; // link to the jquery object of the mapping table
            this.currentPicking; // the selected entry to be picked
            this.currentPickingCell; // link th the jquery object of the table's cell being picked

            this.i = 0
            this.root;
            
            this.tree = d3.layout.tree()
                    .size([this.height, this.width]);
            
            this.diagonal = d3.svg.diagonal()
                    .projection(function(d) { return [d.y, d.x]; });
            
            this.svg = d3.select(this.treeDiv[0]).append("svg")
                    .attr("width", this.width + this.options.margin.right + this.options.margin.left)
                    .attr("height", this.height + this.options.margin.top + this.options.margin.bottom)
                .append("g")
                    .attr("transform", "translate(" + this.options.margin.left + "," + this.options.margin.top + ")");
            
            this.root = this.treeData[0];
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;

            // mapping table related
            this.options.toBeMappedList = Object.keys(this.options.toBeMapped);
            if (this.options.toBeMappedList.length > 0 ) {
                this.instructions = {};
                this.prefillData = {};
                var that = this;
                this.options.toBeMappedList.forEach(function(item, index) {
                    that.instructions[item] = [];
                    //that.prefillData[item] = [];
                    that.itemColors.set(item, that.options.itemColors[index]);
                });

                // draw mapping table
                this.draw_mapping_table();
                this.set_current_mapping_item();
            }

            this.jsonDivIn = $('<div class="jsonDiv panel panel-default panel-body"></div>');
            this.jsonDivIn.css('height', this.options.height/2);
            this.treeDiv.append(this.jsonDivIn);
            var j = this.util.syntaxHighlightJson(this.data);
            this.jsonDivIn.html(j);

            // append result tree if interaction mode is on
            if (this.options.interaction) {
                this.treeDivResult = $('<div class="resultTree"></div>');
                this.jsonDivOut = $('<div class="jsonDiv"></div>');
                this.treeDivResult.append(this.jsonDivOut);
                var child = this.container.find('.treeContainer');
                child.append(
                    this.treeDivResult
                );
                this.update_result_tree();
            }
            this.update(this.root);
        }

        TreeFromJson.prototype = {
            constructor: TreeFromJson,

            update: function(source) {
                var that = this;

                // Compute the new tree layout.
                var nodes = this.tree.nodes(this.root).reverse(),
                    links = this.tree.links(nodes);

                // Compute depth size based on the link name
                var maxSizePerDepth = [];
                nodes.forEach(function(d) {
                    let m = maxSizePerDepth[d.depth] !== undefined ? maxSizePerDepth[d.depth] : 0;
                    let text = that.adjust_text_length(d.linkname).length;
                    let size = d.linkname !== undefined ? text : 0;
                    maxSizePerDepth[d.depth] = size > m ? size : m;
                });
                // add incrementally previous level together
                for (var i=1; i<maxSizePerDepth.length; i++) {
                    maxSizePerDepth[i] += maxSizePerDepth[i-1];
                }

                // Normalize for fixed-depth. (+ consider linkname)
                var depthSepa = maxSizePerDepth.length*100 < this.options.width ? 100 : this.options.width / maxSizePerDepth.length;
                nodes.forEach(function(d) { 
                    //let offset = maxSizePerDepth[d.depth]*(that.options.maxCharDisplay-2);
                    let offset = maxSizePerDepth[d.depth]*(10);
                    d.y = d.depth * depthSepa + offset;
                });

                // Update the nodes…
                var node = this.svg.selectAll("g.node")
                        .data(nodes, function(d) { return d.id || (d.id = ++that.i); });

                /* NODE ENTER */
                // Enter any new nodes at the parent's previous 
                var nodeEnter = node.enter().append("g")
                    .attr("class", "node")
                    .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; });
                // register on click and set correct css class
                if (this.options.interaction) {
                    nodeEnter.filter(function(d) {
                        return d.additionalNode === undefined || !d.additionalNode;
                    })
                    .on("click", function(d, i) { that.click(d, i, this); });
                } else {
                    nodeEnter.attr("class", "node noInteraction");
                }

                var nodeEnterLeaf = nodeEnter.filter(function(d) {
                    var not_add = d.additionalNode === undefined || !d.additionalNode;
                    var is_leaf = d.children === undefined || d.children.length == 0;
                    return  not_add && is_leaf;
                });
                var nodeEnterObject = nodeEnter.filter(function(d) {
                    var not_add = d.additionalNode === undefined || !d.additionalNode;
                    var not_arr = d.children === undefined || d.children[0].linkname === undefined || d.children[0].linkname !== '';
                    var is_obj = d.children !== undefined && d.children[0].linkname !== undefined && d.children[0].linkname !== '';
                    return  not_add && not_arr && is_obj;
                });
                var nodeEnterArray = nodeEnter.filter(function(d) {
                    var not_add = d.additionalNode === undefined || !d.additionalNode;
                    var not_arr = d.children === undefined || d.children[0].linkname === undefined || d.children[0].linkname !== '';
                    return  not_add && !not_arr;
                });
                
                nodeEnterLeaf
                    .append("circle")
                    .attr("r", 1e-6)
                    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

                nodeEnterObject
                    .append("polygon")
                    .attr("points", this.util.getPointsHexagon(0))
                    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

                nodeEnterArray
                    .append("rect")
                    .attr("width", 0)
                    .attr("height", 0)
                    .attr("y", 0)
                    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

                nodeEnter.append("text")
                    .attr("x", function(d) { return d.children || d._children ? -13 : 13; })
                    .attr("dy", ".35em")
                    .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
                    .text(function(d) { return that.adjust_text_length(d.name); })
                    .style("fill-opacity", 1e-6);


                /* NODE UPDATE */
                // Transition nodes to their new position.
                var nodeUpdate = node.transition()
                    .duration(this.options.duration)
                    .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

                nodeUpdate.select("circle")
                    .attr("r", 10)
                    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

                nodeUpdate.select("polygon")
                    .attr("points", this.util.getPointsHexagon(11.5))

                nodeUpdate.select("rect")
                    .attr("width", 20)
                    .attr("height", 20)
                    .attr("y", -10)

                nodeUpdate.select("text")
                    .style("fill-opacity", 1);

                /* NODE EXIT */
                // Transition exiting nodes to the parent's new position.
                var nodeExit = node.exit().transition()
                    .duration(this.options.duration)
                    .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
                    .remove();

                nodeExit.select("circle")
                    .attr("r", 1e-6);

                nodeExit.select("polygon")
                    .attr("points", this.util.getPointsHexagon(0));

                nodeExit.select("rect")
                    .attr("width", 0)
                    .attr("height", 0)
                    .attr("y", 0)

                nodeExit.select("text")
                    .style("fill-opacity", 1e-6);

                // Update the links
                var link = this.svg.selectAll("path.link")
                    .data(links, function(d) { return d.target.id; });

                /* LINK ENTER */
                // Enter any new links at the parent's previous position.
                var linkEnter = link.enter()
                    .insert("g", "g")
                    .attr("class", "linkContainer")
                    .attr("id", function(d) { 
                        let u_id = d.source.id + '-' + d.target.id;
                        return u_id;
                    });

                linkEnter.append("path")
                    .attr("class", "link")
                    .attr("d", function(d) {
                        var o = {x: source.x0, y: source.y0};
                        return that.diagonal({source: o, target: o});
                    });

                linkEnter.append('rect')
                    .attr("class", "rectText linkLabel")
                    .attr("rx", 5)
                    .attr("ry", 5)
                    .attr("transform", function(d) {
                        let xoffset = d.target.linkname !== undefined ? that._letterWidth*that.adjust_text_length(d.target.linkname).length/2 : 0;
                        let yoffset = that.root.y0;
                        return "translate(" +
                            (d.source.y-xoffset) + "," + 
                            (d.source.x-yoffset) + ")";
                        })
                    .style("opacity", 1e-6);

                linkEnter.append('text')
                    .attr("class", "linkText linkLabel")
                    .attr("font-family", "Arial, Helvetica, sans-serif")
                    .attr("fill", "Black")
                    .attr("transform", function(d) {
                        return "translate(" +
                            d.source.y + "," + 
                            d.source.x + ")";
                        })
                    .attr("dy", ".35em")
                    .attr("text-anchor", "middle")
                    .text(function(d) {
                        return that.adjust_text_length(d.target.linkname);
                     })
                    .style("fill-opacity", 1e-6);

                // update rectangle size based on text
                linkEnter.selectAll("rect")
                    .attr("width", function(d) { return d.target.linkname !== undefined ? that._letterWidth*that.adjust_text_length(d.target.linkname).length : 0; })
                    .attr("height", 22)

                // setup onclick on link label
                if (this.options.interaction) {
                    linkEnter.on("click", function(d, i) { 
                        that.clickLabel(d);
                    });
                }

                /* LINK UPDATE */
                // Transition links to their new position.
                var linkUpdate = link;
                linkUpdate.select('path').transition()
                    .duration(this.options.duration)
                    .attr("d", this.diagonal);

                linkUpdate.select('rect').transition()
                    .duration(this.options.duration)
                    .style("opacity", 0.85)
                    .attr("d", this.diagonal)
                    .attr("transform", function(d){
                        let xoffset = d.target.linkname !== undefined ? that._letterWidth*that.adjust_text_length(d.target.linkname).length/2 : 0;
                        let yoffset = 10;
                        return "translate(" +
                            ((d.source.y + d.target.y)/2-xoffset) + "," + 
                            ((d.source.x + d.target.x)/2-yoffset) + ")";
                        }
                    );
                linkUpdate.select('text').transition()
                    .duration(this.options.duration)
                    .style("fill-opacity", 1)
                    .attr("d", this.diagonal)
                    .attr("transform", function(d){
                        return "translate(" +
                            ((d.source.y + d.target.y)/2) + "," + 
                            ((d.source.x + d.target.x)/2) + ")";
                        }
                    );
                    
                /* LINK EXIT */
                // Transition exiting nodes to the parent's new position.
                link.exit().select('path').transition()
                    .duration(this.options.duration)
                    .attr("d", function(d) {
                        var o = {x: source.x, y: source.y};
                        return that.diagonal({source: o, target: o});
                    })
                    .remove();

                // Stash the old positions for transition.
                nodes.forEach(function(d) {
                    d.x0 = d.x;
                    d.y0 = d.y;
                });
            },

            // Given a child, find its index in its parent array (or object key)
            find_child_index: function(child) {
                var c_id = child.id;
                var par = child.parent;
                if (!par) {
                    return;
                }
                var children = par.children;
                for (var i=0; i<children.length; i++) {
                    if (children[i].id == c_id) {
                        var isObj = child.linkname !== undefined && child.linkname !== '';
                        return isObj ? child.linkname : i;
                    }
                }
            },

            // Given a node, find its path to the root
            find_full_path: function(d, res) {
                if (d.parent) {
                    var index = this.find_child_index(d);
                    res.push(index);
                    return this.find_full_path(d.parent, res);
                } else {
                    return res;
                }
            },

            // Toggle children on click.
            click: function(d, i, clickedContext) {
                var that = this;
                var o_depth = d.depth;
                var c_id = d.id;
                var c_index = this.find_child_index(d);
                var clicked = d3.select(clickedContext);
                var itemColor = this.itemColors.get(this.currentPicking);

                this.reset_selected();

                // select all nodes matching the clicked element
                // the selection is based on depth/index/object key
                var resCircle;
                var resRect;
                var resHexa;

                if (clicked.data()[0].children === undefined) { // is leaf
                    resCircle = that.svg.selectAll(".node circle")
                        .filter(function(d) {
                            if (d.depth == 0) {
                                return false;
                            }
                            var c1 = d.depth == o_depth;
                            var c2_childIndexMatch = d.parent.id - c_index -1 == d.id 
                            
                            // is label
                            var c2_isLabel = !Number.isInteger(c_index) && (typeof c_index === 'string');

                            // consider linkname if label has been picked manually
                            let il_last = that.instructions.labels.length-1;
                            var labelIsManual = that.instructions.labels[il_last] != 'l';
                            var c2_manualLabelMatch = true;
                            if (labelIsManual) {
                                c2_manualLabelMatch = d.linkname === c_index; 
                            }

                            var c2 = (c2_childIndexMatch && !c2_isLabel) || (c2_manualLabelMatch && c2_isLabel);
                            var notClicked = d.id != c_id;
                            return c1 && c2;
                        });

                } else { // not leaf but children may be leaves

                    var child = clicked.data()[0].children[0];
                    var children_are_in_array = Array.isArray(child.children);
                    var children_are_in_obj = child.linkname !== undefined && child.linkname !== '';
                    if (children_are_in_obj || children_are_in_array) { // children are not leaves
                        // First child is not a node, should highlight all labels instead

                        var resRect = this.svg.selectAll(".rectText")
                            .filter(function(d) {
                                if (d.depth == 0) {
                                    return false;
                                }
                                var c1 = d.source.depth == o_depth;
                                return c1;
                            });
                        resRect.data().forEach(function(elem) {
                            if (elem.picked !== undefined  && elem.picked != '') {
                                console.log('Possible collision with '+elem.picked);
                            }
                            elem.picked = that.currentPicking;
                        });

                        resCircle = that.svg.selectAll(".node polygon, .node circle")
                            .filter(function(d) {
                                if (d.parent === undefined || d.parent === null) {
                                    return d.id == clicked.data()[0].id;
                                } else {
                                    return d.parent.depth == clicked.data()[0].depth;
                                }
                            });
                        var nodesData = [];
                        if(resCircle !== undefined) {
                            resCircle.data().forEach(function(elem) {
                                if (elem.picked !== undefined  && elem.picked != '') {
                                    console.log('Possible collision with '+elem.picked);
                                }
                                elem.picked = that.currentPicking;
                                nodesData.push(elem);
                            });
                        }

                        // apply coloring
                        if (children_are_in_obj) { // on labels
                            var itemColor = this.itemColors.get(this.currentPicking);
                            var resText = this.svg.selectAll(".linkText")
                                .filter(function(d) {
                                    if (d.depth == 0) {
                                        return false;
                                    }
                                    var c1 = d.source.depth == o_depth;
                                    return c1;
                                });
                            resRect.style('fill', itemColor)
                            resText.style('fill', that.should_invert_text_color(itemColor) ? 'white' : 'black');
                        } else { // on child nodes
                            resCircle.style('fill', itemColor);
                            resCircle.style('fill', that.should_invert_text_color(itemColor) ? 'white' : 'black');
                        }

                        // find all paths
                        var paths = [];
                        nodesData.forEach(function(d, i) {
                            paths[i] = that.find_full_path(d, []);
                        });

                        try {
                            var instructions = this.compute_mapping_instructions(paths);
                        } catch(err) {
                            console.log('Not valid input');
                            var n = clicked.selectAll(".node circle, .node rect, .node polygon");
                            n.style('fill', 'red');
                            return;
                        }
                        this.add_instruction(instructions);
                        return;

                    } else { // children are leaves
                        resCircle = that.svg.selectAll(".node circle")
                            .filter(function(d) {
                                return d.parent !== null && d.parent.id == clicked.data()[0].id;
                            });
                        resRect = that.svg.selectAll(".node rect")
                            .filter(function(d) {
                                return d.parent !== null && d.parent.id == clicked.data()[0].id;
                            });
                    }
                }

                var nodesData = [];
                if(resCircle !== undefined) {
                    resCircle.data().forEach(function(elem) {
                        if (elem.picked !== undefined  && elem.picked != '') {
                            // alert || repick conflicting ????
                            console.log('Possible collision with '+elem.picked);
                            //alert('Possible collision with '+elem.picked);
                        }
                        elem.picked = that.currentPicking;
                        nodesData.push(elem);
                    });

                    resCircle.style('fill', itemColor)
                        .style('fill-opacity', 1.0);
                }
                if(resRect !== undefined) {
                    resRect.data().forEach(function(elem) {
                        if (elem.picked !== undefined  && elem.picked != '') {
                            // alert || repick conflicting ????
                            console.log('Possible collision with '+elem.picked);
                            //alert('Possible collision with '+elem.picked);
                        }
                        elem.picked = that.currentPicking;
                        nodesData.push(elem);
                    });

                    resRect.style('fill', itemColor)
                        .style('fill-opacity', 1.0);

                }

                // find all paths
                var paths = [];
                nodesData.forEach(function(d, i) {
                    paths[i] = that.find_full_path(d, []);
                });
                var instructions = this.compute_mapping_instructions(paths);
                this.unset_related();
                this.add_instruction(instructions);
            },

            clickLabel: function(d) {
                var u_id = d.source.id + '-' + d.target.id;
                var l_id = '#'+u_id;

                var that = this;
                var o_depth = d.source.depth;
                var dest_depth = d.target.depth;
                var c_label = d.target.linkname;
                var c_id = d.source.id;
                var c_index; // no index as the index is the label itself
                var itemColor = this.itemColors.get(this.currentPicking);

                this.reset_selected();

                // select all labels matching the clicked element
                var resRect = this.svg.selectAll(".rectText")
                    .filter(function(d) {
                        if (d.depth == 0) {
                            return false;
                        }
                        var c1 = d.source.depth == o_depth;
                        var c2 = d.target.linkname === c_label;
                        return c1 && c2;
                    });
                var resText = this.svg.selectAll(".linkText")
                    .filter(function(d) {
                        if (d.depth == 0) {
                            return false;
                        }
                        var c1 = d.source.depth == o_depth;
                        var c2 = d.target.linkname === c_label;
                        return c1 && c2;
                    });


                resRect.data().forEach(function(elem) {
                    if (elem.picked !== undefined  && elem.picked != '') {
                        // alert || repick conflicting ????
                        console.log('Possible collision with '+elem.picked);
                        //alert('Possible collision with '+elem.picked);
                    }
                    elem.picked = that.currentPicking;
                });

                resRect.style('fill', itemColor)
                resText.style('fill', that.should_invert_text_color(itemColor) ? 'white' : 'black');

                // find all paths
                var paths = [];
                var nodesCircle = that.svg.selectAll(".node circle").filter(
                        function(d) { 
                            return d.depth == dest_depth && d.linkname == c_label;
                            //return d.depth == dest_depth;
                        }
                );
                nodesCircle.data().forEach(function(d, i) {
                    paths[i] = that.find_full_path(d, []);
                });
                var nodesRect = that.svg.selectAll(".node rect").filter(
                        function(d) {
                            return d.depth == dest_depth && d.linkname == c_label;
                            //return d.depth == dest_depth;
                        }
                );
                nodesRect.data().forEach(function(d, i) {
                    paths[i] = that.find_full_path(d, []);
                });

                //var instructions = this.compute_mapping_instructions(paths);
                //this.add_instruction(instructions);
                this.unset_related();
                this.add_prefill_data([c_label]);

            },

            unset_related: function() {
                var that = this;
                let curPickingBackup = this.currentPicking;
                let refKey = '@'+this.currentPicking;
                this.options.toBeMappedList.forEach(function(itemName) {
                    if (itemName == curPickingBackup) {
                        return true;
                    }
                    let inst = that.options.toBeMapped[itemName].instructions;
                    inst = inst.replace(/>/g, '')
                    let instS = inst.split('.');
                    if (instS.indexOf(refKey) > -1) {
                        that.set_current_mapping_item(itemName);
                        that.reset_selected();
                    }
                });
                this.set_current_mapping_item(curPickingBackup);
            },

            reset_selected: function() {
                var that = this;
                var resNode = that.svg.selectAll(".node circle, .node rect, .node polygon")
                    .filter(function(d) {
                        return d.picked == that.currentPicking;
                    });
                resNode.style('fill', 'white')
                    .style('fill-opacity', 1.00);

                resNode.data().forEach(function(elem) {
                    elem.picked = '';
                });


                var resLabel = that.svg.selectAll(".rectText")
                    .filter(function(d) {
                        return d.picked == that.currentPicking;
                    });
                var resText = that.svg.selectAll(".linkText")
                    .filter(function(d) {
                        return d.picked == that.currentPicking;
                    });

                resLabel.style('fill', null)
                    .style('fill-opacity', null);
                resText.style('fill', 'Black');

                resLabel.data().forEach(function(elem) {
                    elem.picked = '';
                });

                this.unset_related();
                this.add_instruction([]);
            },


            compute_mapping_instructions: function(d) {
                var mapping = [];
                for (var i=0; i<d[0].length; i++) {
                    var prevVal = null;
                    var instruction = null;
                    for (var j=0; j<d.length; j++) {
                        var arr = d[j];
                        if (prevVal === null) {
                            prevVal = arr[i];
                        } else {
                            if (prevVal != arr[i]) { // value different, need to loop over them
                                instruction = 'l'
                                break;
                            }
                        }
                    }
                    instruction = instruction !== null ? instruction : prevVal;
                    mapping.unshift(instruction);
                }

                // if no path found, we are at the root -> need to iterate
                if (mapping.length == 0) {
                    mapping.push('l');
                }

                return mapping;
            },
            

            draw_mapping_table: function() {
                var that = this;
                this.mappingDomTable = $('<table class="table mappingTable"></table>');
                var thead = $('<thead></thead>')
                var tbody = $('<tbody></tbody>')
                var row1 = $('<tr></tr>');
                var row2 = $('<tr style="height: 20px;"></tr>');
                var valueHeader;
                this.options.toBeMappedList.forEach(function(item, index) {
                    var itemColor = that.options.itemColors[index];
                    var cellH = $('<th data-map="'+item+'">'+item+': <span id="'+item+'Cell" data-map="'+item+'" style="font-weight: normal; font-style: italic;"></span> </th>');
                    var cellB2 = $('<td id="'+item+'CellFun" class="cellFunInput" data-map="'+item+'"></td>');
                    var fun_head = $('<span><span style="color: mediumblue;">function</span> (value, datum) {</span>');
                    var fun_foot = $('<span>}</span>');
                    var fun_foot_res = $('<span class="funResText">&gt <span style="color: mediumblue;">function</span> (<span id="funXInput-'+item+'">x</span>, d) = <span id="funXOuput-'+item+'">x</span></span>');
                    var fun_input = $('<textarea id="'+item+'" rows="1"></textarea>');
                    fun_input.val(that.options.default_function);
                    cellB2.append(fun_head);
                    cellB2.append(fun_input);
                    cellB2.append(fun_foot);
                    cellB2.append(fun_foot_res);
                    cellH.click(function() { that.set_current_mapping_item(item); });
                    cellB2.click(function() { that.set_current_mapping_item(item); });
                    that.set_color(cellH, itemColor);
                    that.set_color(cellB2, itemColor);
                    row1.append(cellH);
                    row2.append(cellB2);
                    if (item == 'values') {
                        valueHeader = cellH
                    }
                });
                thead.append(row1);
                tbody.append(row2);
                this.mappingDomTable.append(thead);
                this.mappingDomTable.append(tbody);
                this.fillValueDomInput = $('<input class="form-control fillValue" placeholder="0" value="empty">');
                var configDiv = $('<div class="form-group mappingTableDivConfig"></div>')
                    .append($('<label class="fillValue">Fill value</label>'))
                    .append(this.fillValueDomInput);
                var div = $('<div></div>');
                div.append(this.mappingDomTable);
                if (valueHeader !== undefined) {
                    valueHeader.append(configDiv);
                }
                this.container.prepend(div);

                this.fillValueDomInput.on('input', function() {
                    that.update_result_tree();
                });
                $('.mappingTable textarea').on('input', function() {
                    that.update_result_tree();
                });
            },

            set_color: function(item, color) {
                item.css('background-color', color);
                if (this.should_invert_text_color(color)) {
                    item.css('color', 'white');
                } else {
                    item.css('color', 'black');
                }
            },

            should_invert_text_color: function(color) {
                var colorS = color.replace('#', '');
                var r = parseInt('0x'+colorS.substring(0,2));
                var g = parseInt('0x'+colorS.substring(2,4));
                var b = parseInt('0x'+colorS.substring(4,6));
                var avg = ((2 * r) + b + (3 * g))/6;
                if (avg < 128) {
                    return true;
                } else {
                    return false;
                }
            },

            // if name is empty, select first item not having instructions
            set_current_mapping_item: function(name) {
                if (name === undefined) {
                    for (var entry of this.options.toBeMappedList) {
                        let prefillLength = this.prefillData[entry] !== undefined ? this.prefillData[entry].length : 0;
                        if (this.instructions[entry].length == 0 && prefillLength == 0) {
                            name = entry;
                            break;
                        }
                    }
                    if (name === undefined) { // all items have a mapping, do nothing
                        return;
                    }
                }
                this.mappingDomTable.find('td').addClass('grey');
                this.mappingDomTable.find('th').addClass('grey');
                this.mappingDomTable.find('td').removeClass('picking');
                this.mappingDomTable.find('th').removeClass('picking');
                var cells = this.mappingDomTable.find('[data-map="'+name+'"]');
                var itemColor = this.itemColors.get(name);
                cells.removeClass('grey');
                this.currentPickingCell = this.mappingDomTable.find('#'+name+'Cell');
                this.currentPicking = name;

                //this.mappingDomTable.find('cellFunInput').collapse('hide')
                //this.mappingDomTable.find('#'+name+'CellFun').collapse('show')
            },

            add_instruction: function(instructions) {
                this.instructions[this.currentPicking] = instructions;
                this.currentPickingCell.text(instructions.toString());
                if (instructions.length != 0) {
                    this.set_current_mapping_item();
                    this.update_result_tree();
                }
            },

            add_prefill_data: function(data) {
                this.prefillData[this.currentPicking] = data;
                this.currentPickingCell.text(data.toString());
                this.set_current_mapping_item();
                this.update_result_tree();
            },

            // destroy and redraw
            update_result_tree: function() {
                var options = {
                    interaction: false,
                    //width: this.width,
                    //height: this.height
                    width: this.options.width-30,
                    height: this.options.height
                };

                var continue_update = this.render_functions_output();
                if (!continue_update) {
                    return
                }

                // collect functions
                var functions = {};
                $('.mappingTable textarea').each(function() {
                    var dom = $(this);
                    var f_body = dom.val();
                    functions[dom[0].id] = new Function('value', 'datum', f_body);
                });

                // perform mapping
                var pm_options = {
                    fillValue: this.fillValueDomInput.val(),
                    functions: functions,
                    datum: this.root,
                    prefillData: this.prefillData,
                };
                var adjustedInstructions = this.adjust_instruction();
                var constructionInstruction = this.options.toBeMapped;
                var result = new $.proxyMapper(adjustedInstructions, constructionInstruction, this.data, pm_options);

                // destroy and redraw
                this.treeDivResult[0].innerHTML = '';
                new TreeFromJson(this.treeDivResult, result, options);
            },

            adjust_instruction: function() {
                var that = this;
                var adjustedInstructions = $.extend(true, {}, this.instructions);
                adjustedInstructions.index = {};
                var matchingIndex = 0;

                // convert integer index into {index}
                this.options.toBeMappedList.forEach(function(item) {
                    if (that.options.toBeMapped[item].strategy === 'value') {
                        let arr = adjustedInstructions[item];
                        for (let i=0; i<arr.length; i++) {
                            if (Number.isInteger(arr[i])) {
                                arr[i] = '{'+arr[i]+'}';
                            }
                        }
                        return false;
                    }

                });

                // add labels and values tracking for value strategy only
                var subkeys = {}
                var v, l, d;
                var v_keyname, l_keyname, d_keyname;
                this.options.toBeMappedList.forEach(function(keyname) {
                    var item = that.options.toBeMapped[keyname];
                    if (item.strategy === 'value') {
                        v = that.instructions[keyname];
                        v_keyname = keyname;
                        let s = item.instructions.split('.');
                        if (s.length >= 2 && s[0] === '' && s[1] !== '') {
                            s.slice(1).forEach(function(k) {
                                if (k.substring(0, 2) === '@@' || k.substring(0, 2) === '@>') {
                                    let k_sliced = k.slice(2);
                                    subkeys[k_sliced] = that.instructions[k_sliced];
                                } else if (k[0] === '@') {
                                    let k_sliced = k.slice(1);
                                    subkeys[k_sliced] = that.instructions[k_sliced];
                                }
                            });
                        }
                        return false;
                    }
                });

                for (let keyname in subkeys) {
                    if (this.options.toBeMapped[keyname].strategy === 'date') {
                        var d = this.instructions[keyname];
                        var d_keyname = keyname;
                    } else if (this.options.toBeMapped[keyname].strategy === 'label') {
                        var l = this.instructions[keyname];
                        var l_keyname = keyname;
                    } else {
                        return false;
                    }

                }

                //var l = this.instructions.labels;
                //var v = this.instructions.values;
                //var d = this.instructions.dates;

                // label & value
                if (l !== undefined && l.length != 0 && v.length != 0) {
                    var smaller_array = v.length < l.length ? v : l;
                    var has_matched = false;
                    for (var i=0; i<smaller_array.length; i++) {
                        if (v[i] != l[i]) { 
                            matchingIndex = i-1;
                            has_matched = true;
                            break;
                        }
                    }

                    // in case no match, last one should be registered
                    matchingIndex = has_matched ? matchingIndex : smaller_array.length-1;
                    //let inst = adjustedInstructions.values[matchingIndex];
                    let inst = adjustedInstructions[v_keyname][matchingIndex];
                    inst = inst == 'l' ? 'l' : '{'+inst+'}';
                    //adjustedInstructions.values[matchingIndex] = 'i1,'+inst;
                    let kref = '@'+l_keyname;
                    adjustedInstructions[v_keyname][matchingIndex] = kref + ',' + inst;
                    //adjustedInstructions.index['i1'] = adjustedInstructions.labels.slice(matchingIndex+1);
                    adjustedInstructions.index[kref] = adjustedInstructions[l_keyname].slice(matchingIndex+1);
                }

                var matchingIndex = 0;
                // date & value
                if (d !== undefined && d.length != 0 && v.length != 0) {
                    smaller_array = v.length < d.length ? v : d;
                    for (var i=0; i<smaller_array.length; i++) {
                        if (v[i] != d[i]) { 
                            matchingIndex = i-1;
                            break;
                        }
                    }
                    //adjustedInstructions.values[matchingIndex] = 'i2,'+adjustedInstructions.values[matchingIndex];
                    let kref = '@'+d_keyname;
                    adjustedInstructions[v_keyname][matchingIndex] = kref + ',' + adjustedInstructions[v_keyname][matchingIndex];
                    //adjustedInstructions.index['i2'] = adjustedInstructions.dates.slice(matchingIndex+1);
                    adjustedInstructions.index[kref] = adjustedInstructions[d_keyname].slice(matchingIndex+1);

                    // add '' at the end for value only
                    //var end_i = adjustedInstructions.values.length-1;
                    //var last_i = adjustedInstructions.values[end_i];
                    //var end_i = adjustedInstructions[v_keyname].length-1;
                    //var last_i = adjustedInstructions[v_keyname][end_i];
                    //last_i = last_i.split(',');
                    //last_i = last_i.length == 2 ? last_i[1] : last_i[0];
                    //if (last_i == 'l') {
                    //    //adjustedInstructions.values[end_i+1] = '';
                    //    adjustedInstructions[v_keyname][end_i+1] = '';
                    //}
                }

                // add '' at the end for value only
                if (v !== undefined && v.length > 0) {
                    var end_i = adjustedInstructions[v_keyname].length-1;
                    var last_i = adjustedInstructions[v_keyname][end_i];
                    last_i = last_i.split(',');
                    last_i = last_i.length == 2 ? last_i[1] : last_i[0];
                    if (last_i == 'l') {
                        adjustedInstructions[v_keyname][end_i+1] = '';
                    }
                }

                return adjustedInstructions;
            },

            render_functions_output: function() {
                var that = this;
                var flag_continue = true;
                $('.mappingTable textarea').each(function() {
                    var c_id = $(this).attr('id');
                    var f_body = $(this).val();
                    var funXInput = $('#funXInput-'+c_id);
                    var funXOuput = $('#funXOuput-'+c_id);
                    // check if valid function
                    try {
                        var f = new Function('value', 'datum', f_body);
                        var nodes = that.svg.selectAll(".node, .rectText").filter(
                            function(d) { return d.picked === c_id;}
                        );
                        // fetch first name occurence
                        var d = nodes.data()[0];
                        var x;
                        if (d.source !== undefined && d.target !== undefined) { // is a link label
                            x = d.target.linkname;
                        } else {
                            x = d.name;
                        }
                        funXInput.text('"'+that.adjust_text_length(x)+'"');
                        funXInput[0].innerHTML = '"'+that.adjust_text_length(x)+'"';
                        funXOuput[0].innerHTML = that.adjust_text_length('"'+f(x, d)+'"');
                    } catch(err) { // Error
                        if (err.name == 'SyntaxError') {
                            flag_continue = false;
                            funXOuput[0].innerHTML = $('<span class="funOutputError">'+err.name+'</span>')[0].outerHTML;
                        } else if (err.name == 'TypeError') {
                            funXInput[0].innerHTML = $('<span class="funOutputError">'+'Not picked yet'+'</span>')[0].outerHTML;
                            var html = $('<span></span>');
                            html.append($('<span class="funOutputError">'+'Not picked yet'+'</span>'));
                            html.append($('<span class="funOutputError">'+err.name+'</span>'));
                            funXOuput[0].innerHTML = html[0].outerHTML;
                        } else {
                            funXOuput[0].innerHTML = $('<span class="funOutputError">'+err.name+'</span>')[0].outerHTML;
                        }
                    }
                });
                return flag_continue;
            },

            // return true if the supplied value is an object and not an array
            is_object: function(v) {
                return v !== null && typeof v === 'object' && !Array.isArray(v);
            },

            adjust_text_length: function(text) {
                if (text === undefined || text === '') {
                    return '';
                }
                text = new String(text);
                var textSliced = text.slice(0, this.options.maxCharDisplay);
                if (text.length > this.options.maxCharDisplay) {
                    textSliced += '...';
                }
                return textSliced;
            },

            generate_d3_tree_from_json: function(root, linkname, depth, maxDepth, maxWidth) {
                if (depth == 0) {
                    return;
                }
                var child = {
                    parent: null,
                    linkname: linkname
                };

                var remaining = 0;
                if (Array.isArray(root)) {
                    child.children = [];

                    for (var node of root.slice(0, maxWidth)) {
                        child.children.push(this.generate_d3_tree_from_json(node, '', depth-1, maxDepth, maxWidth));
                    }
                    remaining = root.length - maxWidth;

                } else if (this.is_object(root)) {
                    child.children = [];

                    var i = 0;
                    for (var k in root) {
                        if (i > maxWidth) {
                            break;
                        }
                        var node = root[k];
                        child.children.push(this.generate_d3_tree_from_json(node, k, depth-1, maxDepth, maxWidth));
                        i++;
                    }
                    remaining = Object.keys(root).length - maxWidth;

                } else {
                    child.name = root;
                }

                // add false remaining node
                if (remaining > 0) {
                    var addNode = {};
                    addNode.parent = null;
                    addNode.additionalNode = true;
                    addNode.name = '['+remaining+' more]';
                    child.children.push(addNode);
                }
                return child;
            },

            util: {

                syntaxHighlightJson: function(json) {
                    if (typeof json == 'string') {
                        json = JSON.parse(json);
                    }
                    json = JSON.stringify(json, undefined, 2);
                    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/(?:\r\n|\r|\n)/g, '<br>').replace(/ /g, '&nbsp;');
                    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                            var cls = 'json_number';
                            if (/^"/.test(match)) {
                                if (/:$/.test(match)) {
                                    cls = 'json_key';
                                } else {
                                    cls = 'json_string';
                                }
                            } else if (/true|false/.test(match)) {
                                cls = 'json_boolean';
                            } else if (/null/.test(match)) {
                                cls = 'json_null';
                            }
                            return '<span class="' + cls + '">' + match + '</span>';
                    });
                },

                getPointsHexagon: function(size) {
                    // sin(pi/6) = 0.87, cos(pi/6) ~= 0.5
                    let pts = [
                        0+','+size,
                        size*0.87 + ',' + size*0.5,
                        size*0.87 + ',' + -size*0.5,
                        0 + ',' + -size,
                        -size*0.87 + ',' + -size*0.5,
                        -size*0.87 + ',' + size*0.5,
                    ];
                    return pts.join(', ');
                },

                objkeyToList: function(obj) {

                }



            }


        }

        $.treeFromJson = TreeFromJson;
        $.fn.treeFromJson = function(data, option) {
            var pickerArgs = arguments;
            var tfj;

            this.each(function() {
                var $this = $(this),
                    inst = $this.data('treeFromJson'),
                    options = ((typeof option === 'object') ? option : {});
                if ((!inst) && (typeof option !== 'string')) {
                    tfj = new TreeFromJson($this, data, options);
                    $this.data('treeFromJson', tfj);
                } else {
                    if (typeof option === 'string') {
                        inst[option].apply(inst, Array.prototype.slice.call(pickerArgs, 1));
                    }
                }
            });
            return tfj;
        }
        $.fn.treeFromJson.constructor = TreeFromJson;
    })
);
