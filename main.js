(function ($) {
  
  var graph = null

  "use strict";
  $(window).on('load', function () {

    graph = new G6.Graph({
      container: 'mountNode', // String | HTMLElement, required, the id of DOM element or an HTML node
      width, // Number, required, the width of the graph
      height, // Number, required, the height of the graph
      fitView: true,
      fitViewPadding: [20, 40, 50, 20],
      fitCenter: true,


      // layout: {
      //     type: 'force',
      //     preventOverlap: true,
      //     linkDistance: (d) => {
      //       if (d.source.id === 'node0') {
      //         return 300;
      //       }
      //       return 60;
      //     },
      //     nodeStrength: (d) => {
      //       if (d.isLeaf) {
      //         return -1000;
      //       }
      //       return -800;
      //     },
      //     edgeStrength: (d) => {
      //       if (d.source.id === 'node1' || d.source.id === 'node2' || d.source.id === 'node3') {
      //         return 0.7;
      //       }
      //       return 0.1;
      //     },
      //   },

      modes: {
        default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'activate-relations',
          // {
          //     type: 'tooltip', // Tooltip
          //     formatText(model) {
          //       // The content of tooltip
          //       const text = 'label: ' + model.label + '<br/> class: ' + model.class;
          //       return text;
          //     },
          //   },

        ], // Allow users to drag canvas, zoom canvas, and drag nodes
      },

      theme: {
        type: 'spec',
        specification: {
          node: {
            dataTypeField: 'sortAttr2',
          },
        },
      },

      defaultNode: {

        type: 'circle',

        // type: 'circle',
        size: 50,
        style: {
          fill: '#DEE9FF',
          stroke: '#5B8FF9'
        },
        labelCfg: {
          position: 'bottom',
          style: {
            fontSize: 20,
            fill: '#666',
            stroke: '#eaff8f',
            lineWidth: 5,
          },
        },

      },

      defaultEdge: {
        type: 'quadratic', // assign the edges to be quadratic bezier curves
        style: {
          stroke: '#cfcfcf'
        },
        labelCfg: {
          autoRotate: true,
        },
      },
    });

  });

  const width = document.getElementById('mountNode').scrollWidth;
  const height = document.getElementById('mountNode').scrollHeight || 1000;


  $('form').submit((e) => {
    e.preventDefault();
    let data = $('form').serializeArray();
    if(data.value == ""){
      alert("IP address cannot be empty!")
      return;
    }
    fetch("http://" + data[0].value + "/getTopology", {
      method: "POST",
      body: JSON.stringify({
        userId: 1,
      }),
      headers: {
        "Content-type": "application/json; charset=UTF-8"
      }
    })
      .then((response) => {
        if (!response.ok) {
          alert('Cannot connect to the agent');
        }
        return response.json();
      })
      .then((json) => {
        G6.Util.processParallelEdges(json.edges, 40);
        graph.data(json);
        graph.render();

      });




  });





})(jQuery);








