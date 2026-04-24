/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package argot3NG;

//import goutility4.GOGraphOWL;
//import goutility4.NodeExt;
import java.util.ArrayList;
//import java.util.Collections;
//import java.util.Comparator;
import java.util.List;

/**
 *
 * @author thor
 */
public class Group {

    private final ArrayList<Node> nodes;
    private Node founder;

    public Group() {
        nodes = new ArrayList<>();
    }

    /**
     * @return the nodes
     */
    public ArrayList<Node> getNodes() {
        return nodes;
    }

    /**
     * @param node
     */
    public void addNode(Node node) {
        nodes.add(node);
    }

    public void addNodes(ArrayList<Node> c) {
        nodes.addAll(c);
    }

    /**
     * @return the founder
     */
    public Node getFounder() {
        return founder;
    }

    /**
     * @param founder the founder to set
     */
    public void setFounder(Node founder) {
        this.founder = founder;
    }

    public double getGroupScore() {
        double score = 0.0;
        for (Node n : nodes) {
            score += n.getInc();
        }
        return score;
    }

    public double getOwnGroupScore() {
        double score=0.0;
        for (Node n: nodes) {
            score+=n.getOwnInc();
        }
        return score;
    }
    
    public double getNewOwnGroupScore() {
        double score=0.0;
        for (Node n: nodes) {
            score+=n.getNewOwnInc();
        }
        return score;
    }

    public double getTheoreticalOwnGroupScore() {
        double score=0.0;
        for (Node n: nodes) {
            score += n.getThereticalOwnInc();
        }
        return score;
    }

    public List<Node> getNewNodesOverOwnTS(double ts) {
        List<Node> nn = new ArrayList<>();
        
        for (int i = 0; i < nodes.size(); i++) {
            Node n = nodes.get(i);
            if (n.isRoot()) {
                continue;
            }
            
            if (n.getNewOwnTs() >= ts) {
                nn.add(n);
            }
        }
        return nn;
    }
    
//    public List<Node> getNodesOverOwnTS(double ts) {
//        List<Node> nn = new ArrayList<>();
//        
//        for (int i = 0; i < nodes.size(); i++) {
//            Node n = nodes.get(i);
//            if (n.isRoot()) {
//                continue;
//            }
//            
//            if (n.getOwnTs() >= ts) {
//                nn.add(n);
//            }
//        }
//        return nn;
//    }
    
//    public double getZGroupScore() {
//        double score = 0.0;
//        for (Node n : nodes) {
//            score += n.getZScore();
//        }
//        return score;
//    }

//    public double getGroupTS() {
//        double score=0.0;
//        for (Node n : nodes) {
//            score+=n.getZScore() * n.getIC();
//        }
//        return score;
//    }

//    public double getGroupeAbsoluteScore() {
//        double score=0.0;
//        for (Node n : nodes) {
//            score+=n.getAbsValue();
//        }
//        return score;
//    }
    
//    public ArrayList<Node> getOrderedTSNodes() {
//        if (nodes.size() > 1) {
//            Comparator<Node> com = new TSComparator();
//            Collections.sort(nodes, com);
//        }
//        return nodes;
//    }

//    public List<Node> getOrderedNodesOverTS(int max, double ts) {
//        ArrayList<Node> nn = new ArrayList<>();
//        GOGraphOWL<Node, NodeExt> graph = ArgotOptions.instance().graph;
//        for (int i = 0; i < nodes.size(); i++) {
//            Node n = nodes.get(i);
//            if (n.isRoot()) {
//                continue;
//            }
//            if (n.getTs() >= ts) {
//                nn.add(n);
//            }
//        }
//        
//        for (int i=0; i<nn.size(); i++) {
//            Node n=nodes.get(i);
//            for (int j=i; j<nn.size(); j++) {
//                if (graph.isDescendantOf(nodes.get(j), n)) {
//                    nn.remove(i);
//                }
//            }
//        }
//
//        if (nodes.size() > 1) {
//            Comparator<Node> com = new TSComparator();
//            Collections.sort(nodes, com);
//        }
//
//        return (nn.subList(0, Math.min(max, nn.size())));
//    }

//    public Node getBestNode() {
//        if (nodes.size() > 1) {
//            Comparator<Node> com = new TSComparator();
//            Collections.sort(nodes, com);
//            return nodes.get(nodes.size() - 1);
//        }
//        return nodes.get(0);
//    }

//    public List<Node> getNodesOverOwnTSspecific(double ts) {
//        List<Node> nn = new ArrayList<Node>();
//        List<Node> nnodesc = new ArrayList<Node>();
//
//        GOGraphOWL<Node, NodeExt> graph = ArgotOptions.instance().graph;
//        for (int i = 0; i < nodes.size(); i++) {
//            Node n = nodes.get(i);
//            if (n.isRoot()) {
//                continue;
//            }
//            else if(n.getOwnTs() >= ts) {
//                nn.add(n);
//            }
//        }
//
//        for (int i=0; i<nn.size(); i++) {
//            Node n=nodes.get(i);
//            boolean b = true;
//            for (int j=0; j<nn.size(); j++) {
//                if (graph.isDescendantOf(nodes.get(j), n)) {
////                    nn.remove(i);
//                    b=false;
//                    break;
//                }
//            }
//            if (b) {
//                nnodesc.add(n);
//            }
//        }
//        return nnodesc;
//    }

//    public List<Node> getNodesOverAllTS(double ownts, double ts) {
//        List<Node> nn = new ArrayList<Node>();
//        GOGraphOWL<Node, NodeExt> graph = ArgotOptions.instance().graph;
//        for (int i = 0; i < nodes.size(); i++) {
//            Node n = nodes.get(i);
//            if (n.isRoot()) {
//                continue;
//            }
//            boolean b = true;
//            if (n.getOwnTs() >= ownts || n.getTs() >= ts) {
//                for (int j = i; j < nodes.size(); j++) {
//                    if (graph.isDescendantOf(nodes.get(j), n)) {
//                        b = false;
//                        break;
//                    }
//                }
//                if (b) {
//                    nn.add(n);
//                }
//            }
//        }
//        return nn;
//    }
}
