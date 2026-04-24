/*
 * GORetOptions.java
 *
 * Created on May 4, 2006, 9:04 AM
 *
 * To change this template, choose Tools | Template Manager
 * and open the template in the editor.
 */
package argot3NG;

import goutility4.GOGraphOWL;
import goutility4.NodeExt;
import metrics4.Distance;

/**
 *
 * @author demattel
 */
public class ArgotOptions {

    private static ArgotOptions options = null;

    private ArgotOptions() {
    }

    public static ArgotOptions instance() {
        if (options == null) {
            options=new ArgotOptions();
            return options;
        }
        return options;
    }
    
    String password;
    String userName;
    String serverName;
    String dbName;
    int port = 27017;
//    String tableName;

    String inFileName;
    String outFileName = null;
//    double distValue = 0.70;
//    double mergeValue = 0.60;
    double distValue = 0.90;
    double mergeValue = 0.80;
    int nodesFromGroup;

//    boolean precalc_freq;
//    int idDB;
    String dbResName;

    double intCThreshold = 0.0;
    double infCThreshold = 0.0;
    double tsThreshold = 0.0;

    String goFileName;
//    String measureName = "lin";
    Distance method;
    
//    double gzscore = 0.4;
//    double gscore = 0.4;
    
//    double gzscore = 0.4;
    double gscore = 0.1;
    
    //GOGraph<Node> graph;
    GOGraphOWL<Node, NodeExt> graph;
//    String disjointFile;
//    boolean longestpath = false;
    String collection = "goafreq";
    
    double maxweightscore = 300; // max score assigned by BLAST
//    public boolean hasIntDisjoint() {
//        return disjointFile != null;
//    }
    
    public GOGraphOWL<Node, NodeExt> graphInstance() {
        return graph;
    }
}
