// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ForensiVaultAudit {
    struct AuditEntry {
        string ipfsCid;
        string dataHash;
        uint256 timestamp;
        address operator;
    }

    mapping(string => AuditEntry) private _trails;
    string[] private _jobIds;

    event AuditTrailLogged(
        string indexed jobId,
        string ipfsCid,
        string dataHash,
        uint256 timestamp,
        address operator
    );

    function logAuditTrail(
        string calldata jobId,
        string calldata ipfsCid,
        string calldata dataHash
    ) external {
        _trails[jobId] = AuditEntry(ipfsCid, dataHash, block.timestamp, msg.sender);
        _jobIds.push(jobId);
        emit AuditTrailLogged(jobId, ipfsCid, dataHash, block.timestamp, msg.sender);
    }

    function getAuditTrail(string calldata jobId)
        external view returns (string memory ipfsCid, string memory dataHash, uint256 timestamp)
    {
        AuditEntry memory e = _trails[jobId];
        return (e.ipfsCid, e.dataHash, e.timestamp);
    }

    function getJobCount() external view returns (uint256) {
        return _jobIds.length;
    }
}
