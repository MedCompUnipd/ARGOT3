/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package argot3NG;

import goutility4.GOGraphOWL;
import goutility4.NodeExt;
import java.util.ArrayList;
import java.util.HashSet;
import metrics4.Distance;

/**
 *
 * @author thor
 */
public class GroupNodes {

    private final Distance method;
    private ArrayList<Group> groups;

    public GroupNodes() {
        method = ArgotOptions.instance().method;
    }

    /**
     *
     * @param graph
     * @param blasthits
     */
    public void group(GOGraphOWL<Node, NodeExt> graph, ArrayList<Node> blasthits) {
        groups = new ArrayList<>();
        HashSet<String> hs = new HashSet<>();
        Group g;
        for (int i = 0; i < blasthits.size(); i++) {
            if (!hs.contains(blasthits.get(i).getOntID())) {
                g = new Group();
                g.setFounder(blasthits.get(i));
                g.addNode(blasthits.get(i));
                groups.add(g);
            } else {
                continue;
            }
            
            for (int j = i + 1; j < blasthits.size(); j++) {
                if (!hs.contains(blasthits.get(j).getOntID())) {
                    double dist = method.computeDistance(blasthits.get(i), blasthits.get(j));
                    if (dist >= ArgotOptions.instance().distValue) {
                        g.addNode(blasthits.get(j));
                        hs.add(blasthits.get(j).getOntID());
                    }
                }
            }
        }

        mergeGroups();
    }

    private void mergeGroups() {
        for (int i=0; i<groups.size(); i++) {
            for (int j=i+1; j<groups.size(); j++) {
                if (method.computeDistance(groups.get(i).getFounder(), groups.get(j).getFounder()) >= ArgotOptions.instance().mergeValue) {
                    groups.get(i).addNodes(groups.get(j).getNodes());
                    groups.remove(j);
                }
            }
        }
    }

    public ArrayList<Group> getGroups() {
        return groups;
    }
}
