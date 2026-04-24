package argot3NG;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.io.PrintStream;
import java.util.List;
import java.util.TreeMap;
import java.util.Iterator;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.apache.commons.cli.*;
import exception4.NodeNotFoundException;
import goutility4.GOGraphOWL;
import goutility4.NodeExt;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.MongoClientSettings;
import com.mongodb.client.MongoDatabase;
import com.mongodb.ServerAddress;
import com.mongodb.MongoCredential;
import java.util.Arrays;
import metrics4.SimGIC;
import stats4.GraphFreq;

/**
 *
 * @author thor
 */
public class Main {
    private final Options options;
    private ArgotOptions configOptions;
    private PrintStream out;
//    private TreeMap<String, Double> weights;
    private TreeMap<String, Double> max_weights;
    
    private final GOGraphOWL<Node, NodeExt> graph;
    private final GraphFreq<Node, NodeExt> dag;

    public Main(String[] args) {
        options = new Options();
        configOptions = ArgotOptions.instance();
        initCommandLineOptions();

        if (!parseCommands(args)) {
            printHelp();
            System.exit(-1);
        }

        graph = new GOGraphOWL<>(configOptions.goFileName, Node.class, NodeExt.class);
        
        if (configOptions.method instanceof SimGIC) {
            SimGIC simgic = (SimGIC) configOptions.method;
            simgic.setGraphOWL(graph);
            configOptions.method = simgic;
        }
        
        configOptions.graph = graph;
        MongoClientSettings.Builder settingsBuilder = MongoClientSettings.builder()
                .applyToClusterSettings(builder -> builder.hosts(Arrays.asList(new ServerAddress(configOptions.serverName, configOptions.port))));

        if (configOptions.userName != null && configOptions.password != null) {
            MongoCredential credential = MongoCredential.createCredential(configOptions.userName, configOptions.dbName, configOptions.password.toCharArray());
            settingsBuilder.credential(credential);
        }

        MongoClient mongoClient = MongoClients.create(settingsBuilder.build());
        MongoDatabase database = mongoClient.getDatabase(configOptions.dbName);
        
        dag = GraphFreq.instance();
        dag.init(graph, database, configOptions.collection);
        
//        Disjoint disj = new Disjoint();
//        disj.addDisjoint(graph, 6, 1, 3);

        if (configOptions.outFileName == null) {
            out = new PrintStream(System.out);
        } else {
            try {
                out = new PrintStream(new File(configOptions.outFileName));
            } catch (FileNotFoundException ex) {
                Logger.getLogger(Main.class.getName()).log(Level.SEVERE, null, ex);
            }
        }
        readWeights(configOptions.inFileName);
    }

    private void initCommandLineOptions() {
        options.addOption("i", "input", true, "The input file with weights");
        options.addOption("s", "server", true, "The database server for existing GOA tables");
        options.addOption("d", "dbname", true, "The name of the database");
        options.addOption("u", "username", true, "The username to access the database");
        options.addOption("p", "password", true, "The password to access the database");
        options.addOption("P", "port", true, "The port to access the database");
        options.addOption("o", "output", true, "The output file");
        //GO dag options
        options.addOption("g", "gofile", true, "The GO OBO file");
        options.addOption("l", "distance", true, "The distance threshold for inclusion into a group");
        options.addOption("e", "merge_distance", true, "The distance threshold for merging two groups");

        options.addOption("m", "ssmesure", true, "The semantic similarity mesure to use (simgic)");
        // thresholds
        options.addOption("r", "ts_thr", true, "Sets the minimum threshold for the total score");
        options.addOption("h", "infC_thr", true, "Sets the minimum threshold for the information content");
        options.addOption("k", "intC_thr", true, "Sets the minimum threshold for the internal confidence");

        options.addOption("n", "gscore", true, "Group score based on InC");
        options.addOption("c", "collection", true, "The names of the collection with GO count");
    }

    private boolean parseCommands(String[] args) {
        CommandLineParser cmdparser = new DefaultParser();
        try {
            CommandLine cmd = cmdparser.parse(options, args);
            
            if (cmd.hasOption("i")) {
                configOptions.inFileName = cmd.getOptionValue("i");
            } else {
                return false;
            }
            
            if (cmd.hasOption("s")) {
                configOptions.serverName = cmd.getOptionValue("s");
            } else {
                return false;
            }
            
            if (cmd.hasOption("d")) {
                configOptions.dbName = cmd.getOptionValue("d");
            } else {
                return false;
            }
            
            if (cmd.hasOption("u")) {
                configOptions.userName = cmd.getOptionValue("u");
            }
            
            if (cmd.hasOption("p")) {
                configOptions.password = cmd.getOptionValue("p");
            }

            if (cmd.hasOption("P")) {
                configOptions.port = Integer.parseInt(cmd.getOptionValue("P"));
            }
            
            if (cmd.hasOption("c")) {
                configOptions.collection = cmd.getOptionValue("c");
            }
            
            if (cmd.hasOption("o")) {
                configOptions.outFileName = cmd.getOptionValue("o");
            } else {
                return false;
            }
            
            if (cmd.hasOption("g")) {
                configOptions.goFileName = cmd.getOptionValue("g");
            } else {
                return false;
            }
            
            if (cmd.hasOption("m")) {
                switch (cmd.getOptionValue("m")) {
                        case "simgic":
                            configOptions.method = new SimGIC();
                            break;
                        default:
                            return false;
                }
            } else {
                configOptions.method = new SimGIC();
            }
            
            if (cmd.hasOption("l")) {
                configOptions.distValue = Double.parseDouble(cmd.getOptionValue("l"));
            }
            if (cmd.hasOption("e")) {
                configOptions.mergeValue = Double.parseDouble(cmd.getOptionValue("e"));
            }
            if (cmd.hasOption("r")) {
                configOptions.tsThreshold = Double.parseDouble(cmd.getOptionValue("r"));
            }
            if (cmd.hasOption("h")) {
                configOptions.infCThreshold = Double.parseDouble(cmd.getOptionValue("h"));
            }
            if (cmd.hasOption("k")) {
                configOptions.intCThreshold = Double.parseDouble(cmd.getOptionValue("k"));
            }
            if (cmd.hasOption("n")) {
                configOptions.gscore = Double.parseDouble(cmd.getOptionValue("n"));
            }
            return true;
        } catch (ParseException ex) {
            Logger.getLogger(Main.class.getName()).log(Level.SEVERE, null, ex);
            return false;
        }
    }

    private void readWeights(String file) {
        String header = null;
        TreeMap<String, Double> weights = new TreeMap<>();
        TreeMap<String, Double> theoreticlWeights = new TreeMap<>();
        max_weights = new TreeMap<>();
        
        out.println("#Seq ID\tGOID\tOntology\tInf. Content\tTotal Score\tInt. Confidence\tGScore\tTheoretical TS");
        try {
            FileReader fr = new FileReader(file);
            BufferedReader br = new BufferedReader(fr);
            String line;
            int n = 0;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.startsWith(">") && n > 0) {
                    BuildWeightGraph bwg = null;
                    try {
                        bwg = new BuildWeightGraph(graph, weights, theoreticlWeights);
                    } catch (NodeNotFoundException ex) {
                        Logger.getLogger(Main.class.getName()).log(Level.SEVERE, null, ex);
                    }
                    writeResults(header, bwg);
                    graph.cleanAll();
                    weights.clear();
                    theoreticlWeights.clear();
                    max_weights.clear();
                    header = line.substring(1);
                    continue;
                } else if (line.startsWith(">")) {
                    ++n;
                    header = line.substring(1);
                    continue;
                }

                if (line.equals(""))
                    continue;
                
                String[] data = line.split("\\s+");

                Double w = Double.parseDouble(data[1]);
                if (w > 0) {                    
                    if (weights.containsKey(data[0])) {
                        weights.put(data[0], weights.get(data[0]) + w);
                        theoreticlWeights.put(data[0], theoreticlWeights.get(data[0]) + configOptions.maxweightscore);
                    } else {
                        weights.put(data[0], w);
                        theoreticlWeights.put(data[0], configOptions.maxweightscore);
                    }
                }
                if (max_weights.containsKey(data[0])) {
                    max_weights.put(data[0], Math.max(max_weights.get(data[0]), w));
                } else {
                    max_weights.put(data[0], w);
                }
            }

            BuildWeightGraph bwg = null;
            try {
                bwg = new BuildWeightGraph(graph, weights, theoreticlWeights);
            } catch (NodeNotFoundException ex) {
                Logger.getLogger(Main.class.getName()).log(Level.SEVERE, null, ex);
            }
            writeResults(header, bwg);

        } catch (FileNotFoundException ex) {
            Logger.getLogger(Main.class.getName()).log(Level.SEVERE, null, ex);
        } catch (IOException ie) {
            Logger.getLogger(Main.class.getName()).log(Level.SEVERE, null, ie);
        }
    }

    private void writeResults(String header, BuildWeightGraph bwg) {
        double ts;
        double tsTheoretical;
        double newts;
        
        for (Group g : bwg.getGroup()) {
//            if (g.getGroupScore() >= configOptions.gscore) {
    //            List<Node> nn = g.getNodesOverOwnTS(0.0);
                List<Node> nn = g.getNodes();
                for (Node n : nn) {
                    ts = n.getOwnTs() * (n.getOwnInc() / g.getOwnGroupScore()) * max_weights.get(n.getOntID());
                    tsTheoretical = n.getThereticalOwnTs() * (n.getThereticalOwnInc() / g.getTheoreticalOwnGroupScore()) * configOptions.maxweightscore;
                    newts = n.getNewOwnTs() * (n.getNewOwnInc() / g.getTheoreticalOwnGroupScore()) * max_weights.get(n.getOntID());
                    
//                    if (ts >= configOptions.tsThreshold && n.getIC() >= configOptions.infCThreshold && n.getInc() >= configOptions.intCThreshold) {
                        String namespace = "";
                        switch (n.getNameSpace()) {
                            case biological_process:
                                namespace = "P";
                                break;
                            case molecular_function:
                                namespace = "M";
                                break;
                            case cellular_component:
                                namespace = "C";
                                break;
                        }
//                        double ratios = ts / tsTheoretical;
                        double ratios = newts / tsTheoretical;
                        out.println(header + "\t" + n.getOntID() + "\t" + namespace + "\t" + n.getIC() + "\t" + ts + "\t" + n.getInc() + "\t" + g.getGroupScore() + "\t" + ratios);
//                    }
                }
//            }
        }
    }

    public final void printHelp() {
        Iterator<Option> iter = options.getOptions().iterator();
        while (iter.hasNext()) {
            Option o = iter.next();
            if (!o.getOpt().equals(" ")) {
                System.err.println("-" + o.getOpt() + "\t" + "--" + o.getLongOpt() + "\t" + o.getDescription());
            } else {
                System.err.println("\t" + "--" + o.getLongOpt() + "\t" + o.getDescription());
            }
        }
    }

    /**
     * @param args the command line arguments
     */
    public static void main(String[] args) {
        new Main(args);
    }
}
