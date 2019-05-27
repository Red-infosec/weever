from weever.APFS.APFS_filesystem.Container_Superblock import Superblock
from weever.APFS.APFS_filesystem.Node import Node
#from weever.APFS.APFS_filesystem.Volume_Superblock import vSuperblock
from weever.APFS.APFS_filesystem.Object_Map import ObjectMap


class InodeTable:

    def __init__(self, fs_stream):
        self.mainContainerBlock = Superblock(fs_stream, 0)
        self.data = Superblock(fs_stream, 0).parse_superblock(fs_stream, 0)
        self.blocksize = self.data["block_size"]
        self.CMAP = ObjectMap(fs_stream, self.mainContainerBlock.getObjectMapAdr(), self.blocksize)
        self.cmapDATA = self.CMAP.parseObjectMap(fs_stream, self.mainContainerBlock.getObjectMapAdr())
        self.cmapRootNode = self.cmapDATA["root"]


    def getAllInodes(self, fs_stream):
    # gets all Inodes from volumes
        inodeAddressList = []
        # inodeAddressList contains address to block as well as offset to inode in tuple)
        listOfVolumes = self.CMAP.mapCObjectMap(fs_stream)
        # list of all volumes with their oids attached
        volumeMapList = []
        rootNodeList = []
        # lists of all volume maps and rootnodes
        for d, y in listOfVolumes:
                volumeMapList.append(d["omap_oid"])
                rootNodeList.append(d["root_tree_oid"])

        vmapRootNode = []
        vmapList = []
        for i in range (0, len(volumeMapList)):
            vmap = ObjectMap(fs_stream, volumeMapList[i]*self.blocksize, self.blocksize).parseObjectMap(fs_stream,
                                                                                                        volumeMapList[i]
                                                                                                        *self.blocksize)
            vmapList.append(vmap)

        for i in range (0, len(vmapList)):
            vrootnode = Node(fs_stream, vmapList[i]["root"]*self.blocksize, self.blocksize).parseNode(fs_stream,
                                                                                                      vmapList[i][
                                                                                                          "root"] * self
                                                                                                      .blocksize)
            vmapRootNode.append(vrootnode)


        oidList = []
        # list of oid addresses linked to by volume omap root nodes
        for i in range(0, len(vmapRootNode)):
            entries = vmapRootNode[i]["entry_count"]
            for j in range(0, entries):
                oidList.append((vmapRootNode[i]["oid " + str(j)], vmapRootNode[i]["omv_paddr " + str(j)]))
            if oidList[0][0] == rootNodeList[i]:
                notNeeded = oidList.pop(0)
                #get rid of rootnode since it has nothing of value for inode table

        for i in range(0, len(oidList)):
            temp = Node(fs_stream, oidList[i][1]*self.blocksize, self.blocksize).parseNode(fs_stream, oidList[i][1]*
                                                                                           self.blocksize)
            for j in range(0, temp["entry_count"]):
                if temp["kind " + str(j)] >> 28 == 3:
                    inodeAddressList.append((oidList[i][1]*self.blocksize, self.blocksize -
                                             temp["data_offset " + str(j)] - 40 * (temp["node_type"] & 1)))

        return inodeAddressList