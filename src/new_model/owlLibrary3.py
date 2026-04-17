#!/usr/bin/env python3
#  -------------------------------------------------------------------------------
#  Name:        GoOwl library
#  Purpose:     parsing go*.owl file
#
#  Author:      stefano, emilio
#
#  Created:     21/05/2019
#  Last update: 18/04/2024
#  Last check:	18/04/2024
#  Copyright:   (c) stefano 2019
#  Licence:     GPL
#  -------------------------------------------------------------------------------

import math
import copy
from owlready2 import *
from collections import defaultdict

def e_print(*args, **kwargs):
    # print to standard error
    print(*args, file=sys.stderr, **kwargs)
    sys.exit()


class GoOwl:

    def __init__(self, owl, namespace="http://purl.obolibrary.org/obo/", goa_file='', by_ontology=False, use_all_evidence=True,
                 valid_evidence=('EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP', 'TAS', 'IC'), edges=('is a', 'part of'), logging=False):
        self.__owl = owl
        self.__ns = namespace
        self.__global = {}
        self.__global_total = {}
        self.__deprecated = defaultdict(set)
        self.__obsolete = defaultdict(set)
        self.__triplets_son_father = defaultdict(set)
        self.__triplets_father_son = defaultdict(set)
        self.__triplets_son_father_go_only = defaultdict(set)
        self.__triplets_father_son_go_only = defaultdict(set)
        self.__secondary_ids_to_primary = {}
        self.__primary_to_secondary_ids = defaultdict(set)
        self.__mf_root = 'GO_0003674'
        self.__bp_root = 'GO_0008150'
        self.__cc_root = 'GO_0005575'
        self.__roots = {'GO_0008150', 'GO_0003674', 'GO_0005575'}
        self.__depths = {}
        self.__depths_fingerprint = [False, False]
        self.__valid_edges = set(e for e in edges)
        self.__valid_evidence = set(valid_evidence)  # GOA evidence codes used for the IC computation
        self.__by_ontology = by_ontology
        self.__use_all_evidence = use_all_evidence
        self.__file_extension = str(owl).strip().split('.')[-1]
        self.__ontology_converter = {'BPO': 'biological_process', 'MFO': 'molecular_function',
                                     'CCO': 'cellular_component', 'B': 'biological_process', 'P': 'biological_process',
                                     'M': 'molecular_function', 'F': 'molecular_function', 'C': 'cellular_component'}
        self.__logging = logging
        self.__loading()
        self.__ic_gos = {}
        self.__gos_ic = {}
        if len(goa_file) > 0:
            self.compute_ic(goa_file)

    #  END DEF

    def __loading(self):
        if len(self.__ns) == 0:
            e_print('Namespace required. Use "http://purl.obolibrary.org/obo/" as namespace.')

        go_load = get_ontology(self.__owl).load()

        # SEPARATE OBSOLETE AND DEPRECATED FROM THE TOTAL
        for go_term in go_load.classes():
            self.__global_total[go_term.name] = go_term
            if go_term.label.first():
                if go_term.label.first().startswith("obsolete"): # -> OBSOLETE NODE
                    if go_term.consider:
                        for alt in [a.replace(':', '_') for a in go_term.consider]:
                            self.__obsolete[go_term.name].add(alt)
                    else:
                        self.__obsolete[go_term.name].add('unreferenced')
                else: # -> NOT OBSOLETE, NOT DEPRECATED
                    self.__global[go_term.name] = go_term
                    if len(go_term.hasAlternativeId) > 0:
                        for owl_alt_id in [str(alt_id).replace(':', '_') for alt_id in go_term.hasAlternativeId]:
                            self.__secondary_ids_to_primary[owl_alt_id] = go_term.name
                            self.__primary_to_secondary_ids[go_term.name].add(owl_alt_id)
            else: # -> DEPRECATED
                self.__deprecated[go_term.name].add(go_term.IAO_0100001.first().name)

        for go_name_son, go_son in self.__global.items():
            detail_description = self.go_single_details(go_name_son)
            go_dict_parents = self.__go_parents(go_son)
            if go_dict_parents:
                for go_name_parent, details in go_dict_parents.items():

                    #  triplets  SON -> FATHERS
                    self.__triplets_son_father[go_name_son].add((go_name_parent, details['rel'], details['namespace'], details['name'], details['descr']))
                    self.__triplets_son_father_go_only[go_name_son].add(go_name_parent)

                    #  triplets  FATHER -> SONS
                    self.__triplets_father_son[go_name_parent].add((go_name_son, details['rel'], detail_description['namespace'], detail_description['name'], detail_description['descr']))
                    self.__triplets_father_son_go_only[go_name_parent].add(go_name_son)

    def __go_parents(self, go_concept):
        parents = {}
        #  try to record here specific restrictions of this GO
        for parent in go_concept.is_a:
            if isinstance(parent, Restriction):
                if not isinstance(parent.value, Not):
                    rel = parent.property.label.first()
                    if rel == 'part of' or rel.find('regulates') >= 0 or rel == 'occurs in' or rel.find('capable of') >= 0: # capable of may be non-existent
                        parents[parent.value.name] = {'rel': rel,
                                                      'name': parent.value.label.first(),
                                                      'descr': parent.value.IAO_0000115.first(),
                                                      'namespace': parent.value.hasOBONamespace.first()}

            else: # -> not isinstance(parent, Restriction):
                if parent.name.startswith("GO_"):
                    parents[parent.name] = {'rel': 'is a',
                                            'name': parent.label.first(),
                                            'descr': parent.IAO_0000115.first(),
                                            'namespace': parent.hasOBONamespace.first()}


        for equiv in go_concept.INDIRECT_equivalent_to:
            for equiv_parent in equiv.Classes:
                if isinstance(equiv_parent, Restriction):
                    rel = equiv_parent.property.label.first()
                    if rel == 'part of' or rel.find('regulates') >= 0 or rel == 'occurs in' or rel.find('capable of') >= 0: # capable of may be non-existent
                        parents[equiv_parent.value.name] = {'rel': rel,
                                                            'name': equiv_parent.value.label.first(),
                                                            'descr': equiv_parent.value.IAO_0000115.first(),
                                                            'namespace': equiv_parent.value.hasOBONamespace.first()}

        return parents


    def go_single_details(self, go_name):
        go_term = self.__global[go_name]
        orig_details = {'GO': go_name,
                        'name': go_term.label.first(),
                        'descr': go_term.IAO_0000115.first(),
                        'namespace': go_term.hasOBONamespace.first()}

        return orig_details

    def get_obsolete_deprecated_list(self):
        return self.__obsolete, self.__deprecated

    def get_go_son_father(self):
        return self.__triplets_son_father_go_only

    def get_go_father_son(self):
        return self.__triplets_father_son_go_only

    def get_sons(self):
        return self.__triplets_father_son

    def get_secondary_ids(self):
        return self.__secondary_ids_to_primary

    def get_go(self, go):
        return self.__global_total[go]

    def get_go_id(self, go):
        return self.__global_total[go].name

    def is_secondary_id(self, go_name):
        return go_name in self.__secondary_ids_to_primary

    def get_primary_go_from_secondary_id(self, go_name):
        if not self.is_secondary_id(go_name):
            return None
        return self.__secondary_ids_to_primary[go_name]

    def get_secondary_ids_from_go(self, go_name):
        if go_name not in self.__primary_to_secondary_ids:
            return set()
        return self.__primary_to_secondary_ids[go_name]

    def listing(self, ontology='', exclude_roots=False, total=True):
        listing_data = {}
        starting_data = self.__global_total if total else self.__global
        for go, data in starting_data.items():
            if ontology and data['namespace'] != ontology:
                continue
            if exclude_roots and go in self.__roots:
                continue
            listing_data[go] = data
        return listing_data

    def get_leaves(self, ontology=''):
        leaves = set()
        if ontology:
            if not ontology in ['biological_process', 'molecular_function', 'cellular_component']:
                print(f'Valid ontology names are: biological_process, molecular_function, cellular_component')
                print('Function get_leaves_by_ontology will exit returning an empty set')
                return leaves()
            else:
                for go_id, sons_data in self.__global.items():
                    if self.go_single_details(go_id)['namespace'] == ontology and len(self.__triplets_father_son_go_only[go_id]) == 0:
                        leaves.add(go_id)
        else:
            for go_id, sons_data in self.__global.items():
                if len(self.__triplets_father_son_go_only[go_id]) == 0:
                    leaves.add(go_id)

        return leaves

    def get_children(self, go, by_ontology=False, valid_edges=False):
        go_done = {}
        if go not in self.__triplets_father_son and go not in self.__secondary_ids_to_primary:
            if self.__logging:
                print(f'WARNING: GO term {go} seems not to exist. Returning empty dictionary')
            return go_done

        if go in self.__secondary_ids_to_primary:
            go = self.__secondary_ids_to_primary[go]

        if not go in self.__triplets_father_son.keys():
            if self.__logging:
                print(f'WARNING: GO term {go} has no children. Returning empty dictionary')
            return go_done
        else:
            go_children = self.__triplets_father_son[go]
            for go_p in go_children:
                if by_ontology and self.go_single_details(go)['namespace'] != go_p[2]:
                    continue
                if valid_edges and go_p[1] not in self.__valid_edges:
                    continue

                go_done[go_p[0]] = {'rel': go_p[1], 'name': go_p[3], 'descr': go_p[4], 'namespace': go_p[2]}

            return go_done

    def get_children_id(self, go, by_ontology=False, valid_edges=False):
        return set(self.get_children(go, by_ontology=by_ontology, valid_edges=valid_edges))

    def get_parents(self, go, by_ontology=False, valid_edges=False):
        go_done = {}
        if go not in self.__triplets_son_father and go not in self.__secondary_ids_to_primary:
            if self.__logging:
                print(f'WARNING: GO term {go} seems not to exist. Returning empty dictionary')
            return go_done

        if go in self.__secondary_ids_to_primary:
            go = self.__secondary_ids_to_primary[go]

        if not go in self.__triplets_son_father.keys():
            if self.__logging:
                print(f'WARNING: GO term {go} has no fathers. Returning empty dictionary')
            return go_done
        else:
            go_fathers = self.__triplets_son_father[go]
            for go_f in go_fathers:
                if by_ontology and self.go_single_details(go)['namespace'] != go_f[2]:
                    continue
                if valid_edges and go_f[1] not in self.__valid_edges:
                    continue

                go_done[go_f[0]] = {'rel': go_f[1], 'name': go_f[3], 'descr': go_f[4], 'namespace': go_f[2]}

            return go_done

    def get_parents_id(self, go, by_ontology=False, valid_edges=False):
        return set(self.get_parents(go, by_ontology=by_ontology, valid_edges=valid_edges))

    def get_descendants(self, go, by_ontology=False, valid_edges=False):
        if go not in self.__triplets_father_son and go not in self.__secondary_ids_to_primary:
            if self.__logging:
                print(f'WARNING: GO term {go} seems not to exist. Returning empty dictionary')
            return {}

        if go in self.__secondary_ids_to_primary:
            go = self.__secondary_ids_to_primary[go]

        if go not in self.__triplets_father_son:
            if self.__logging:
                print(f'WARNING: GO term {go} has no descendants. Returning empty dictionary')
            return {}

        go_list = set()
        visited = set()

        go_list.update(self.get_children_id(go, by_ontology=by_ontology, valid_edges=valid_edges))
        descendants = {child: data for child, data in self.get_children(go, by_ontology=by_ontology, valid_edges=valid_edges).items()}
        while go_list:
            current = go_list.pop()
            if current not in visited:
                go_list.update(self.get_children_id(current, by_ontology=by_ontology, valid_edges=valid_edges))
                descendants.update({child: data for child, data in self.get_children(current, by_ontology=by_ontology, valid_edges=valid_edges).items()})
                visited.add(current)

        return descendants

    def get_descendants_id(self, go, by_ontology=False, valid_edges=False):
        return set(self.get_descendants(go, by_ontology=by_ontology, valid_edges=valid_edges).keys())

    def get_ancestors(self, go, by_ontology=False, valid_edges=False):
        if go not in self.__triplets_son_father and go not in self.__secondary_ids_to_primary:
            if self.__logging:
                print(f'WARNING: GO term {go} seems not to exist. Returning empty dictionary')
            return {}

        if go in self.__secondary_ids_to_primary:
            go = self.__secondary_ids_to_primary[go]

        if go not in self.__triplets_son_father:
            if self.__logging:
                print(f'WARNING: GO term {go} has no descendants. Returning empty dictionary')
            return {}

        go_list = set()
        visited = set()

        go_list.update(self.get_parents_id(go, by_ontology=by_ontology, valid_edges=valid_edges))
        ancestors = {parent: data for parent, data in self.get_parents(go, by_ontology=by_ontology, valid_edges=valid_edges).items()}
        while go_list:
            current = go_list.pop()
            if current not in visited:
                go_list.update(self.get_parents_id(current, by_ontology=by_ontology, valid_edges=valid_edges))
                ancestors.update({parent: data for parent, data in self.get_parents(current, by_ontology=by_ontology, valid_edges=valid_edges).items()})
                visited.add(current)

        return ancestors

    def get_ancestors_id(self, go, by_ontology=False, valid_edges=False):
        return set(self.get_ancestors(go, by_ontology=by_ontology, valid_edges=valid_edges).keys())

    def compute_depth(self, by_ontology=False, valid_edges=False):
        self.__depths_fingerprint = [by_ontology, valid_edges]
        for root in self.__roots:
            self.__depths[root] = 0
            go_terms = list(self.get_children_id(root, by_ontology=by_ontology, valid_edges=valid_edges))
            level = 1
            while go_terms:
                for _ in range(len(go_terms)):
                    go = go_terms.pop(0)
                    if go not in self.__depths:
                        self.__depths[go] = level
                    else:
                        self.__depths[go] = max([self.__depths[go], level])
                    go_terms.extend(list(self.get_children_id(go, by_ontology=by_ontology, valid_edges=valid_edges)))
                level += 1

    def get_depth(self, go):
        if not self.__depths:
            print('You musu call the "compute_depth()" method before (defaults to by_ontology=False, valid_edges=False)')
            return None
        try:
            return self.__depths[go]
        except KeyError:
            return None

    def travel_by_distance(self, go, by_ontology=False, valid_edges=False):
        if not self.__depths or self.__depths_fingerprint != [by_ontology, valid_edges]:
            self.compute_depth(by_ontology=by_ontology, valid_edges=valid_edges)

        ups = self.get_parents_id(go, by_ontology=by_ontology, valid_edges=valid_edges)
        downs = self.get_children_id(go, by_ontology=by_ontology, valid_edges=valid_edges)

        direct_ups = {up for up in ups if abs(self.__depths[up] - self.__depths[go]) == 1}
        jump_ups = {up for up in ups if abs(self.__depths[up] - self.__depths[go]) != 1}
        direct_downs = {down for down in downs if abs(self.__depths[down] - self.__depths[go]) == 1}
        jump_downs = {down for down in downs if abs(self.__depths[down] - self.__depths[go]) != 1}

        return {'direct_ups': direct_ups - jump_ups, 'jump_ups': jump_ups, 'direct_downs': direct_downs - jump_downs, 'jump_downs': jump_downs}

    def get_gos_by_distance(self, go, d=1, by_ontology=False, valid_edges=False):
        neighbors = self.travel_by_distance(go, by_ontology=by_ontology, valid_edges=valid_edges)
        direct_ups, jump_ups = neighbors['direct_ups'], neighbors['jump_ups']
        direct_downs, jump_downs = neighbors['direct_downs'], neighbors['jump_downs']
        siblings = set()

        edge_direct_ups = direct_ups.copy()
        edge_direct_downs = direct_downs.copy()
        edge_jump_ups = jump_ups.copy()
        edge_jump_downs = jump_downs.copy()
        expanded = set(go)

        d += -1
        while(d):
            new_direct_ups, new_jump_ups = set(), set()
            new_direct_downs, new_jump_downs = set(), set()
            new_siblings = set()

            dus = [self.travel_by_distance(term, by_ontology=by_ontology, valid_edges=valid_edges) for term in edge_direct_ups]
            jus = [self.travel_by_distance(term, by_ontology=by_ontology, valid_edges=valid_edges) for term in edge_jump_ups]
            dds = [self.travel_by_distance(term, by_ontology=by_ontology, valid_edges=valid_edges) for term in edge_direct_downs]
            jds = [self.travel_by_distance(term, by_ontology=by_ontology, valid_edges=valid_edges) for term in edge_jump_downs]
            expanded.update(edge_direct_ups.union(edge_jump_ups.union(edge_direct_downs.union(edge_jump_downs))))

            for dup in dus:
                new_direct_ups.update(dup['direct_ups'])
                new_jump_ups.update(dup['jump_ups'])
                new_siblings.update(dup['direct_downs'].union(dup['jump_downs']))
            for ddown in dds:
                new_direct_downs.update(ddown['direct_downs'])
                new_jump_downs.update(ddown['jump_downs'])
                new_siblings.update(ddown['direct_ups'].union(ddown['jump_ups']))
            for jup in jus:
                new_jump_ups.update(jup['direct_ups'].union(jup['jump_ups']))
                new_siblings.update(jup['direct_downs'].union(jup['jump_downs']))
            for jdown in jds:
                new_jump_downs.update(jdown['direct_downs'].union(jdown['jump_downs']))
                new_siblings.update(jdown['direct_ups'].union(jdown['direct_downs']))

            direct_ups.update(new_direct_ups)
            direct_downs.update(new_direct_downs)
            edge_direct_ups = direct_ups - expanded
            edge_direct_downs = direct_downs - expanded

            jump_ups.update(set(new_jump_ups - set(direct_ups.union(expanded))))
            jump_downs.update(set(new_jump_downs - set(direct_downs.union(expanded))))
            edge_jump_ups = jump_ups - expanded - edge_direct_ups
            edge_jump_downs = jump_downs - expanded - edge_direct_downs

            for cross in new_siblings:
                distance = self.__depths[go] - self.__depths[cross]
                if distance == 0:
                    siblings.add(cross)
                elif cross not in direct_ups and cross not in direct_downs and cross not in jump_ups and cross not in jump_downs:
                    if distance > 0:
                        jump_ups.add(cross)
                    else:
                        jump_downs.add(cross)

            d += -1

        return {'direct_ups': direct_ups - siblings,
                'jump_ups': jump_ups - siblings,
                'direct_downs': direct_downs - siblings,
                'jump_downs': jump_downs - siblings,
                'siblings': siblings}

    def go_taxon_constraints(self, go_name):
        if 'go-plus' not in self.__owl:
            e_print('The method go_taxon_constraints only works with the go-plus.')
        taxon_constraints = {}
        i = 1
        if go_name in self.__global.keys():
            go_concept = self.__global[go_name]
            taxon = go_concept.RO_0002161
            for i in range(len(taxon)):
                taxon[i] = int(str(taxon[i]).strip().split('/')[-1].strip().split('_')[-1])

            for parent in go_concept.is_a:
                print(type(parent))
                if isinstance(parent, Restriction):
                    if isinstance(parent.value, Not):
                        if parent.property.label.first().find('taxon') >= 0:
                            taxon_constraints[i] = {'rel': 'Never ' + parent.property.label.first(),
                                                    'taxonId': parent.value.Class.name,
                                                    'taxonName': parent.value.Class.label.first()}
                            i += 1
                    else:
                        if parent.property.label.first().find('taxon') >= 0:
                            taxon_constraints[i] = {'rel': parent.property.label.first(),
                                                    'taxonId': parent.value.name,
                                                    'taxonName': parent.value.label.first()}
                            i += 1

        return taxon_constraints

    ################################################################################################
    #  CUMULATIVE MEMORY AWARE (as if it were a hierarchy rather than a graph)                     #
    ################################################################################################

    def cumulative_freq_prior(self, memory_less=False):
        cumulative = {}
        for go in self.__global:
            cumulative[go] = 1
        for go in self.__global:
            self.bfs_prior(go, cumulative, memory_less=memory_less)
        return cumulative

    def bfs_prior(self, start, cumulative, memory_less=False):
        visited = set()
        queue = [start]
        while queue:
            vertex = queue.pop(0)
            if not memmory_less:
                if vertex not in visited:
                    if vertex != srart:
                        cumulative[vertex] += 1
                    visited.add(vertex)
                    queue.extend(self.__triplets_son_father_go_only[vertex] - visited)
            else:
                if vertex != start:
                    cumulative[vertex] += 1
                queue.extend(self.__triplets_son_father_go_only[vertex])

    def cumulative_freq_corpus(self, list_goa, memory_less=False, by_ontology=False):
        cumulative = {}
        for go in self.__global:
            if go in list_goa:
                cumulative[go] = list_goa[go]
            else:
                cumulative[go] = 0
        for go in self.__global:
            self.bfs_corpus(go, cumulative, list_goa, memory_less=memory_less, by_ontology=by_ontology)
        return cumulative

    def bfs_corpus(self, start, cumulative, list_goa, memory_less=False, by_ontology=False):
        if start in self.__secondary_ids_to_primary:
            start = self.__secondary_ids_to_primary[start]

        ontology = self.go_single_details(start)['namespace']
        visited = set()
        queue = [start]
        add = 0
        if start in list_goa:
            add = list_goa[start]
        while queue:
            vertex = queue.pop(0)
            if not memory_less:
                if vertex not in visited and vertex != start:
                    cumulative[vertex] += add
                    visited.add(vertex)
                    extending = self.__triplets_son_father_go_only[vertex] - visited
            else:
                if vertex != start:
                    cumulative[vertex] += add
                extending = [go for go in self.__triplets_son_father_go_only[vertex] if self.go_single_details(go)['namespace'] == ontology] if by_ontology else self.__triplets_son_father_go_only[vertex]
            queue.extend(extending)

    def compute_simgic(self, go_1, go_2):
        if self.__by_ontology:
            set_1 = self.get_ancestors_id(go_1, by_ontology=True, valid_edges=True)
            set_2 = self.get_ancestors_id(go_1, by_ontology=True, valid_edges=True)
        else:
            set_1 = self.go_ancestors_id(go_1)
            set_2 = self.go_ancestors_id(go_2)

        set_1.add(go_1)
        set_2.add(go_2)
        intersect = set_1.intersection(set_2)
        union = set_1.union(set_2)
        ic_intersect = 0.0
        ic_union = 0.0

        for item in intersect:
            if item in self.__gos_ic:
                ic_intersect += self.__gos_ic[item]

        for item in union:
            if item in self.__gos_ic:
                ic_union += self.__gos_ic[item]

        try:
            return ic_intersect / ic_union
        except ZeroDivisionError:
            return 0.0

    def compute_ic(self, goa_file):
        gos = {}
        with open(goa_file, 'r') as GOA:
            for line in GOA:
                if line.startswith('!'):
                    continue

                data = line.strip().split('\t')
                if len(data) > 5:
                    if not self.__use_all_evidence:
                        if data[3] == 'NOT' or data[6] not in self.__valid_evidence or data[6] in {'ND', 'NR'}:
                            continue
                    else:
                        if data[3] == 'NOT' or data[6] in {'ND', 'NR'}:
                            continue

                    go = data[4].replace(':', '_')
                else:
                    go = data[1].replace(":", "_")

                if go in self.__secondary_ids_to_primary:
                    go = self.__secondary_ids_to_primary[go]

                if go not in gos:
                    gos[go] = 1
                else:
                    gos[go] += 1

        if self.__by_ontology:
            cumulative = self.cumulative_freq_corpus(gos, memory_less=True, by_ontology=True)
        else:
            cumulative = self.cumulative_freq_corpus(gos, memory_less=True)

        for go in cumulative:
            sub_ontology = self.go_single_details(go)['namespace']
            frequency = cumulative[go]

            if sub_ontology == 'molecular_function':
                ic = - math.log((frequency + 1) / (cumulative[self.__mf_root] + 1))
                self.__gos_ic[go] = ic

            elif sub_ontology == 'biological_process':
                ic = - math.log((frequency + 1) / (cumulative[self.__bp_root] + 1))
                self.__gos_ic[go] = ic

            elif sub_ontology == 'cellular_component':
                ic = - math.log((frequency + 1) / (cumulative[self.__cc_root] + 1))
                self.__gos_ic[go] = ic

    def get_gos_ic(self):
        return self.__gos_ic

    def get_go_ic(self, go_id):
        if self.is_secondary_id(go_id):
            go_id = self.__secondary_ids_to_primary[go_id]
        try:
            return self.__gos_ic[go_id]
        except KeyError:
            return 0.0

    def get_gos_in_ic_range(self, low=0, hi=sys.float_info.max, ontology=''):
        gos = set()
        for go, ic in self.__gos_ic.items():
            if ontology and self.go_single_details(go)['namespace'] != ontology:
                continue
            if low <= ic <= hi:
                gos.add(go)
        return gos
# END CLASS
