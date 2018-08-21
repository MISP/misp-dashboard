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
                width: 800,
                height: 800,
                treeNodes : {
                    width: 3,
                    depth: 5
                },
                itemColors: ['#fc440f', '#a5e12e', '#5d2e8c', '#2ec4b6', '#65524d', '#adcad6', '#99c24d'],
                duration: 500,
                interaction: true,
                toBeMapped: []
            };
            this.options = $.extend({}, this._default_options, options);

            this.data = data;
            this.treeData = [this.create_tree(data, '', this.options.treeNodes.depth, this.options.treeNodes.depth, this.options.treeNodes.width)];

            this.letterWidth = 10;
            this.width = this.options.width - this.options.margin.right - this.options.margin.left,
            this.height = this.options.height - this.options.margin.top - this.options.margin.bottom;

            this.itemColors = new Map();
            this.mappingDomTable;
            this.currentPicking;
            this.currentPickingCell;

            this.i = 0
            this.root;
            
            this.tree = d3.layout.tree()
                    .size([this.height, this.width]);
            
            this.diagonal = d3.svg.diagonal()
                    .projection(function(d) { return [d.y, d.x]; });
            
            this.svg = d3.select(this.container[0]).append("svg")
                    .attr("width", this.width + this.options.margin.right + this.options.margin.left)
                    .attr("height", this.height + this.options.margin.top + this.options.margin.bottom)
                .append("g")
                    .attr("transform", "translate(" + this.options.margin.left + "," + this.options.margin.top + ")");
            
            this.root = this.treeData[0];
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;

            if (this.options.toBeMapped.length > 0 ) {
                this.instructions = {};
                var that = this;
                this.options.toBeMapped.forEach(function(item, index) {
                    that.instructions[item] = [];
                    that.itemColors.set(item, that.options.itemColors[index]);
                });

                // draw mapping table
                this.draw_mapping_table();
                this.set_current_mapping_item();
            }

            if (this.options.interaction) {
                //var result = new $.proxyMapper(this.instructions, this.treeData, {});
                this.treeDivResult = $('<div class="resultTree"></div>');
                this.container.append(this.treeDivResult);
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

                // Normalize for fixed-depth.
                nodes.forEach(function(d) { d.y = d.depth * 100; });

                // Update the nodes…
                var node = this.svg.selectAll("g.node")
                        .data(nodes, function(d) { return d.id || (d.id = ++that.i); });

                // Enter any new nodes at the parent's previous 
                var nodeEnter = node.enter().append("g")
                    .attr("class", "node")
                    .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; });
                if (this.options.interaction) {
                    nodeEnter.filter(function(d) {
                        return d.additionalNode === undefined || !d.additionalNode;
                    })
			.on("click", function(d, i) { that.click(d, i, this); });
                } else {
                    nodeEnter.attr("class", "node nodeNoInteraction");
                }

                nodeEnter.filter(function(d) {
		    return d.additionalNode === undefined || !d.additionalNode;
		})
		    .append("circle")
                    .attr("r", 1e-6)
                    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

                nodeEnter.append("text")
                    .attr("x", function(d) { return d.children || d._children ? -13 : 13; })
                    .attr("dy", ".35em")
                    .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
                    .text(function(d) { return d.name; })
                    .style("fill-opacity", 1e-6);


                // Transition nodes to their new position.
                var nodeUpdate = node.transition()
                    .duration(this.options.duration)
                    .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

                nodeUpdate.select("circle")
                    .attr("r", 10)
                    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; });

                nodeUpdate.select("text")
                    .style("fill-opacity", 1);

                // Transition exiting nodes to the parent's new position.
                var nodeExit = node.exit().transition()
                    .duration(this.options.duration)
                    .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
                    .remove();

                nodeExit.select("circle")
                    .attr("r", 1e-6);

                nodeExit.select("text")
                    .style("fill-opacity", 1e-6);

                // Update the links...
                var link = this.svg.selectAll("path.link")
                    .data(links, function(d) { return d.target.id; });

                // Enter any new links at the parent's previous position.
                var linkEnter = link.enter().insert("g", "g");
                linkEnter.append("path")
                    .attr("class", "link")
                    .attr("d", function(d) {
                        var o = {x: source.x0, y: source.y0};
                        return that.diagonal({source: o, target: o});
                    });


                linkEnter.append('rect')
                    .attr("class", "rectText")
                    .attr("transform", function(d) {
                        return "translate(" +
                            d.source.y + "," + 
                            d.source.x + ")";
                        })
                    .style("fill-opacity", 1e-6);
                linkEnter.append('text')
                    .attr("class", "linkText")
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
                        return d.target.linkname;
                     })
                    .style("fill-opacity", 1e-6);

                // update rectangle size based on text
                linkEnter.selectAll("rect")
                    .attr("width", function(d) { return d.target.linkname !== undefined ? that.letterWidth*d.target.linkname.length : 0; })
                    .attr("height", 22)


                // Transition links to their new position.
                var linkUpdate = link;
                linkUpdate.select('path').transition()
                    .duration(this.options.duration)
                    .attr("d", this.diagonal);

                linkUpdate.select('rect').transition()
                    .duration(this.options.duration)
                    .style("fill-opacity", 1)
                    .attr("d", this.diagonal)
                    .attr("transform", function(d){
                        let xoffset = d.target.linkname !== undefined ? that.letterWidth*d.target.linkname.length/2 : 0;
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

            find_child_index: function(child) {
                var c_id = child.id;
                var par = child.parent;
                if (!par) {
                    return;
                }
                var children = par.children;
                for (var i=0; i<children.length; i++) {
                    if (children[i].id == c_id) {
                        return i;
                        break;
                    }
                }
            },

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

                var res;
                if (clicked.data()[0].children === undefined) { // is leaf
                    res = d3.selectAll(".node circle")
                        .filter(function(d) {
                            if (d.depth == 0) {
                                return false;
                            }
                            var c1 = d.depth == o_depth;
                            var c2 = d.parent.id - c_index -1 == d.id;
                            var notClicked = d.id != c_id;
                            return c1 && c2;
                        });
                } else {
                    res = d3.selectAll(".node circle")
                        .filter(function(d) {
                            return d.parent !== null && d.parent.id == clicked.data()[0].id;
                        });
                }

                res.data().forEach(function(elem) {
                    if (elem.picked !== undefined  && elem.picked != '') {
                        // alert || repick conflicting ????
                        console.log('Possible collision with '+elem.picked);
                        //alert('Possible collision with '+elem.picked);
                    }
                    elem.picked = that.currentPicking;
                });

                res.style('fill', itemColor)
                    .style('fill-opacity', 0.85);

                // find all paths
                var paths = [];
                var nodes = d3.selectAll(".node circle").filter(
                        function(d) { return d.picked == that.currentPicking;}
                );
                nodes.data().forEach(function(d, i) {
                    paths[i] = that.find_full_path(d, []);
                });
                var instructions = this.compute_mapping_instructions(paths);
                this.add_instruction(instructions);
            },

            reset_selected: function() {
                var that = this;
                var res = d3.selectAll(".node circle")
                    .filter(function(d) {
                        return d.picked == that.currentPicking;
                    });
                res.style('fill', 'white')
                    .style('fill-opacity', 1.00);

                res.data().forEach(function(elem) {
                    elem.picked = '';
                });

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
                            if (prevVal != arr[i]) { // value different, nood to loop over them
                                instruction = 'l'
                                break;
                            }
                        }
                    }
                    instruction = instruction !== null ? instruction : prevVal;
                    mapping.unshift(instruction);
                }
                return mapping;
            },
            

            draw_mapping_table: function() {
                var that = this;
                this.mappingDomTable = $('<table class="table mappingTable"></table>');
                var thead = $('<thead></thead>')
                var tbody = $('<thead></thead>')
                var row1 = $('<tr></tr>');
                var row2 = $('<tr style="height: 20px;"></tr>');
                this.options.toBeMapped.forEach(function(item, index) {
                    var itemColor = that.options.itemColors[index];
                    var cellH = $('<th>'+item+'</th>');
                    var cellB = $('<td id="'+item+'Cell"></td>');
                    cellH.click(function() { that.set_current_mapping_item(item); });
                    cellB.click(function() { that.set_current_mapping_item(item); });
                    that.set_color(cellH, itemColor);
                    that.set_color(cellB, itemColor);
                    row1.append(cellH);
                    row2.append(cellB);
                });
                thead.append(row1);
                tbody.append(row2);
                this.mappingDomTable.append(thead);
                this.mappingDomTable.append(tbody);
                this.fillValueDomInput = $('<input class="form-control" placeholder="0" value=0>');
                var configDiv = $('<div class="form-group mappingTableDivConfig"></div>')
                    .append($('<label>Fill value</label>'))
                    .append(this.fillValueDomInput);
                var div = $('<div></div>');
                div.append(this.mappingDomTable);
                div.append(configDiv);
                this.container.prepend(div);

                this.fillValueDomInput.on('input', function() {
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
                    for (var entry of this.options.toBeMapped) {
                        if (this.instructions[entry].length == 0) {
                            name = entry;
                            break;
                        }
                    }
                    if (name === undefined) { // all items have a mapping, do nothing
                        return;
                    }
                }
                this.mappingDomTable.find('td').addClass('grey');
                this.mappingDomTable.find('td').removeClass('picking');
                var cell = this.mappingDomTable.find('#'+name+'Cell');
                var itemColor = this.itemColors.get(name);
                cell.removeClass('grey');
                this.currentPickingCell = cell;
                this.currentPicking = name;
            },

            add_instruction: function(instructions) {
                this.instructions[this.currentPicking] = instructions;
                this.currentPickingCell.text(instructions.toString());
                this.set_current_mapping_item();
                this.update_result_tree();
            },

            // destroy and redraw
            update_result_tree: function() {
                var options = {
                    interaction: false
                };

                var adjusted_instructions = $.extend(true, {}, this.instructions);
                var res=[];
                var l = adjusted_instructions.labels;
                var v = adjusted_instructions.values;
                for (var i=0; i<v.length; i++) {
                    if (l[i] != v[i]) { res.push(v[i]); }
                }
                adjusted_instructions.values = res;

                var res=[];
                var matchingIndex;
                var l = adjusted_instructions.labels;
                var v = adjusted_instructions.dates;
                for (var i=0; i<v.length; i++) {
                    if (l[i] != v[i]) { 
                        if (matchingIndex === undefined) {
                            matchingIndex = i-1;
                        }
                        res.push(v[i]);
                    }
                }
                adjusted_instructions.dateFromNode = res;
                adjusted_instructions.labels[matchingIndex] = 'd';


                //var result = new $.proxyMapper(this.instructions, this.data, {});
                var pm_options = {
                    fillValue: this.fillValueDomInput.val() ? this.fillValueDomInput.val() : 0
                };
                var result = new $.proxyMapper(adjusted_instructions, this.data, pm_options);
                this.treeDivResult[0].innerHTML = '';
                new TreeFromJson(this.treeDivResult, result, options);
            },

            isObject: function(v) {
                return v !== null && typeof v === 'object';
            },

            create_tree: function(root, linkname, depth, maxDepth, maxWidth) {
                if (depth == 0) {
                    return;
                }
                var child = {
                    parent: null,
                    linkname: linkname
                };

                if (Array.isArray(root)) {
                    child.children = [];

                    for (var node of root.slice(0, maxWidth)) {
                        child.children.push(this.create_tree(node, '', depth-1, maxDepth, maxWidth));
                    }
                    if (root.length > maxWidth) {
                        var addNode = {};
                        addNode.name = '...';
                        addNode.parent = null;
                        addNode.additionalNode = true;
                        child['children'].push(addNode);
                    }

                } else if (this.isObject(root)) {
                    child.children = [];

                    var i = 0;
                    for (var k in root) {
                        if (i > maxWidth) {
                            break;
                        }
                        var node = root[k];
                        child.children.push(this.create_tree(node, k, depth-1, maxDepth, maxWidth));
                        i++;
                    }
                    if (root.length > maxWidth) {
                        var addNode = {};
                        addNode.name = '...';
                        addNode.parent = null;
                        addNode.additionalNode = true;
                        child.children.push(addNode);
                    }

                } else {
                    child.name = root;
                }
                return child;
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
