import logging
import math
import typing as typ

from weever.ext2.ext2_filesystem.EXT2 import EXT2

LOGGER = logging.getLogger("ext2-osd2")


class EXT4OSD2Metadata:
    """
    holds inode numbers which hold the hidden data in.
    """
    def __init__(self, d: dict = None):
        """
        :param d: dict, dictionary representation of a EXT4OSD2Metadata
                  object
        """
        if d is None:
            # self.inode_table = None
            self.inode_numbers = []
        else:
            # self.inode_table = d["inode_table"]
            self.inode_numbers = d["inode_numbers"]

    def add_inode_number(self, inode_number: int) -> None:
        """
        adds a block to the list of blocks
        :param block_id: int, id of the block
        """
        self.inode_numbers.append(inode_number)

    def get_inode_numbers(self) \
            -> []:
        """
        returns list of inode_numbers
        :returns: list of inode_numbers
        """
        return self.inode_numbers

class EXT4OSD2:
    """
        Hides data in osd2 field of inodes in the first inode_table.
    """
    def __init__(self, stream: typ.BinaryIO, dev: str):
        """
        :param dev: path to an ext2 filesystem
        :param stream: filedescriptor of an ext2 filesystem
        """
        self.dev = dev
        self.stream = stream
        self.ext4fs = EXT4(stream, dev)
        self.inode_table = self.ext4fs.inode_tables[0]

    def write(self, instream: typ.BinaryIO) -> EXT4OSD2Metadata:
        """
        writes from instream into the last two bytes of inodes osd2 field.
        This method currently supports only data sizes less than 4000 bytes.
        :param instream: stream to read from
        :return: EXT4OSD2Metadata
        """
        metadata = EXT4OSD2Metadata()
        instream = instream.read()

        if not self._check_if_supported(instream):
            raise IOError("The hiding data size is currently not supported")


        instream_chunks = [instream[i:i+2] for i in range(0, len(instream), 2)]
        # print(instream_chunks)
        inode_number = 1
        hidden_chunks = 0

        while hidden_chunks < len(instream_chunks):
            chunk = instream_chunks[hidden_chunks]

            if self._write_to_osd2(chunk, inode_number):
                metadata.add_inode_number(inode_number)
                hidden_chunks += 1

            inode_number += 1

        return metadata

    def read(self, outstream: typ.BinaryIO, metadata: EXT4OSD2Metadata) \
            -> None:
        """
        writes data hidden in osd2 blocks into outstream
        :param outstream: stream to write into
        :param metadata: EXT4OSD2Metadata object
        """
        inode_numbers = metadata.get_inode_numbers()
        # print(inode_numbers)
        for nr in inode_numbers:
            outstream.write(self._read_from_osd2(nr))

    def clear(self, metadata: EXT4OSD2Metadata) -> None:
        """
        clears the osd2 field in which data has been hidden
        :param metadata: EXT4OSD2Metadata object
        """
        inode_numbers = metadata.get_inode_numbers()
        for nr in inode_numbers:
            self._clear_osd2(nr)

    def info(self, metadata: EXT4OSD2Metadata = None) -> None:
        """
        shows info about inode osd2 fields and data hiding space
        :param metadata: EXT4OSD2Metadata object
        """
        print("Inodes: " + str(self.ext4fs.superblock.data["inode_count"]))
        print("Total hiding space in osd2 fields: " + str((self.ext4fs.superblock.data["inode_count"]) * 2) + " Bytes")
        if metadata != None:
            filled_inode_numbers = metadata.get_inode_numbers()
            print('Used: ' + str(len(filled_inode_numbers) * 2) + ' Bytes')

    def _write_to_osd2(self, instream_chunk, inode_nr) -> bool:
        # print(instream_chunk)
        self.stream.seek(0)
        total_osd2_offset = self._get_total_osd2_offset(inode_nr)
        # print(total_osd2_offset)
        self.stream.seek(total_osd2_offset)
        if self.stream.read(2) == b'\x00\x00':
            self.stream.seek(total_osd2_offset)
            # print(self.stream.read(12))
            self.stream.write(instream_chunk)
            return True
        else:
            return False

    def _clear_osd2(self, inode_nr: int):
        total_osd2_offset = self._get_total_osd2_offset(inode_nr)
        self.stream.seek(total_osd2_offset)
        self.stream.write(b"\x00\x00")

    def _read_from_osd2(self, inode_nr: int):
        self.stream.seek(0)
        total_osd2_offset = self._get_total_osd2_offset(inode_nr)
        self.stream.seek(total_osd2_offset)
        data = self.stream.read(2)
        # print(data)
        return data

    def _get_total_osd2_offset(self, inode_nr: int) -> int:
        inode_size = self.ext4fs.superblock.data["inode_size"]
        # print("table start", self.inode_table.table_start)

        return self.inode_table.inodes[inode_nr].offset + 0x74 + 0xA

    def _check_if_supported(self, instream) -> bool:
        if len(instream) >= ((self.ext4fs.superblock.data["inode_count"]) * 2):
            return False
        else:
            return True