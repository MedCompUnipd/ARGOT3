/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package argot3NG;

import goutility4.NodeWeight;

/**
 *
 * @author thor
 */
public class Node extends NodeWeight {
    private double inc = 0.0;
//    private double ts=0;
    private double ownweight = 0.0;
    private double owninc = 0.0;
    private double ownTs = 0.0;
    
    private double theoreticalWeight = 0.0;
    private double thereticalInc = 0.0;
    private double thereticalOwnWeight = 0.0;
    private double thereticalOwnInc = 0.0;
    private double thereticalOwnTs = 0.0;
    
    private double newinc = 0.0;
    private double newowninc = 0.0;
    private double newownTs = 0.0;
    

    /**
     * @return the thereticalInc
     */
    public double getThereticalInc() {
        return thereticalInc;
    }

    /**
     * @param thereticalInc the thereticalInc to set
     */
    public void setThereticalInc(double thereticalInc) {
        this.thereticalInc = thereticalInc;
    }

    /**
     * @return the thereticalOwnWeight
     */
    public double getThereticalOwnWeight() {
        return thereticalOwnWeight;
    }

    /**
     * @param thereticalOwnWeight the thereticalOwnWeight to set
     */
    public void setThereticalOwnWeight(double thereticalOwnWeight) {
        this.thereticalOwnWeight = thereticalOwnWeight;
    }

    /**
     * @return the thereticalOwnInc
     */
    public double getThereticalOwnInc() {
        return thereticalOwnInc;
    }

    /**
     * @param thereticalOwnInc the thereticalOwnInc to set
     */
    public void setThereticalOwnInc(double thereticalOwnInc) {
        this.thereticalOwnInc = thereticalOwnInc;
    }

    /**
     * @return the thereticalOwnTs
     */
    public double getThereticalOwnTs() {
        return thereticalOwnTs;
    }

    /**
     * @param thereticalOwnTs the thereticalOwnTs to set
     */
    public void setThereticalOwnTs(double thereticalOwnTs) {
        this.thereticalOwnTs = thereticalOwnTs;
    }

    /**
     * @return the inc
     */
    public double getInc() {
        return inc;
    }

    /**
     * @param inc the inc to set
     */
    public void setInc(double inc) {
        this.inc = inc;
    }

    public void setOwnWeight(double w) {
        this.ownweight = w;
    }

    public double getOwnWeight() {
        return ownweight;
    }

    /**
     * @return the owninc
     */
    public double getOwnInc() {
        return owninc;
    }

    /**
     * @param owninc the owninc to set
     */
    public void setOwnInc(double owninc) {
        this.owninc = owninc;
    }

    /**
     * @return the ownTs
     */
    public double getOwnTs() {
        return ownTs;
    }

    /**
     * @param ownTs the ownTs to set
     */
    public void setOwnTs(double ownTs) {
        this.ownTs = ownTs;
    }
    
    /**
     * @return the theoreticalscore
     */
    public double getTheoreticalWeight() {
        return theoreticalWeight;
    }

    /**
     * @param teoreticalscore the theoreticalscore to set
     */
    public void addTheoreticalWeight(double teoreticalscore) {
        this.theoreticalWeight += teoreticalscore;
    }

    @Override
    public void clean() {
        super.clean();
        inc = 0.0;
//        ts=0;
        ownweight = 0.0;
        owninc = 0.0;
        ownTs = 0.0;
        
        theoreticalWeight = 0.0;
        thereticalInc = 0.0;
        thereticalOwnWeight = 0.0;
        thereticalOwnInc = 0.0;
        thereticalOwnTs = 0.0;
        
        newinc = 0.0;
        newowninc = 0.0;
        newownTs = 0.0;
    }
    
    public double getNewInc() {
        return newinc;
    }

    /**
     * @param newinc the inc to set
     */
    public void setNewInc(double newinc) {
        this.newinc = newinc;
    }

    /**
     * @return the newowninc
     */
    public double getNewOwnInc() {
        return newowninc;
    }

    /**
     * @param newowninc the newowninc to set
     */
    public void setNewOwnInc(double newowninc) {
        this.newowninc = newowninc;
    }

    /**
     * @return the newownTs
     */
    public double getNewOwnTs() {
        return newownTs;
    }

    /**
     * @param newownTs the newownTs to set
     */
    public void setNewOwnTs(double newownTs) {
        this.newownTs = newownTs;
    }

}
