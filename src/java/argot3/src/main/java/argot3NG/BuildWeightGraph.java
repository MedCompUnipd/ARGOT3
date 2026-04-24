/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package argot3NG;

import goutility4.Edge;
import java.util.ArrayList;
import java.util.TreeMap;
import java.util.HashSet;
import goutility4.GOGraphOWL;
import goutility4.NodeExt;
import goutility4.OntNamespace;

/**
 *
 * @author thor
 */
public class BuildWeightGraph {

    private final GOGraphOWL<Node, NodeExt> graph;
    private ArrayList<Group> group;
    private final HashSet<String> visited;
//    private final double theoreticalscore;
//    private double totp;
//    private double totm;
//    private double totc;

    public BuildWeightGraph(GOGraphOWL<Node, NodeExt> graph, TreeMap<String, Double> weights, TreeMap<String, Double> theoreticlWeights) throws exception4.NodeNotFoundException {
        this.graph = graph;
        ArrayList<Node> nodes = new ArrayList<>();
//        this.theoreticalscore = ArgotOptions.instance().maxweightscore;
        group = new ArrayList<>();
        visited = new HashSet<>();
//        totp = 0.0;
//        totm = 0.0;
//        totc = 0.0;
        
        for (String goid : weights.keySet()) {
            if (graph.exists(goid)) {
//                if (null != graph.getGONode(goid).getNameSpace()) switch (graph.getGONode(goid).getNameSpace()) {
//                    case biological_process:
//                        totp += weights.get(goid);
//                        break;
//                    case molecular_function:
//                        totm += weights.get(goid);
//                        break;
//                    case cellular_component:
//                        totc += weights.get(goid);
//                        break;
//                    default:
//                        break;
//                }
                
                graph.getGONode(goid).setOwnWeight(weights.get(goid));
                graph.getGONode(goid).setThereticalOwnWeight(theoreticlWeights.get(goid));
                addWeights(graph.getGONode(goid), weights.get(goid), theoreticlWeights.get(goid));
                visited.clear();
                nodes.add(graph.getGONode(goid));
            }
       }

        setScores(OntNamespace.biological_process);
        setScores(OntNamespace.molecular_function);
        setScores(OntNamespace.cellular_component);

        GroupNodes gn = new GroupNodes();
        gn.group(graph, nodes);
        group = gn.getGroups();
    }

    private void addWeights(Node node, double w, double theoreticalweigth) {
        node.addWeight(w);
        node.addTheoreticalWeight(theoreticalweigth);
        node.setFlag(true);
        visited.add(node.getOntID());
        for (Edge<Node> e : graph.getGOParents(node)) {
            if (!visited.contains(e.getNode().getOntID())) {
                addWeights(e.getNode(), w, theoreticalweigth);
            }
        }
    }

    private void setScores(OntNamespace namespace) {
        double rootWeight = graph.getRoot(namespace).getWeight();
        double rootTheoreticalWeight = graph.getRoot(namespace).getTheoreticalWeight();

        calcScore(graph.getRoot(namespace), rootWeight, rootTheoreticalWeight);
    }

    private void calcScore(Node node, double rootWeight, double rootTheoreticalWeight) {
//        if (node.getZScore() < 0)
//            node.setTs(0);
//        else
//            node.setTs(node.getIC() * node.getZScore());
        
        node.setInc(node.getWeight() / rootWeight);
        node.setOwnInc(node.getOwnWeight() / rootWeight);
        node.setOwnTs(node.getIC() * (node.getOwnInc() * 10));
        
        node.setNewInc(node.getWeight() / rootTheoreticalWeight);
        node.setNewOwnInc(node.getOwnWeight() / rootTheoreticalWeight);
        node.setNewOwnTs(node.getIC() * (node.getNewOwnInc() * 10));
        
        node.setThereticalInc(node.getTheoreticalWeight() / rootTheoreticalWeight);
        node.setThereticalOwnInc(node.getThereticalOwnWeight() / rootTheoreticalWeight);
        node.setThereticalOwnTs(node.getIC() * (node.getThereticalOwnInc() * 10));
        
        for (Edge<Node> e : graph.getGOChildren(node)) {
            if (e.getNode().isFlagged()) {
                calcScore(e.getNode(), rootWeight, rootTheoreticalWeight);
            }
        }
    }
        
   public ArrayList<Group> getGroup() {
       return group;
   }
}
